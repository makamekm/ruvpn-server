package main

import (
	"context"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/openlibrecommunity/olcrtc/mobile"
)

const uriPrefix = "olcrtc://"

type connection struct {
	carrier   string
	transport string
	room      string
	client    string
	key       string
	dns       string
	vp8FPS    int
	vp8Batch  int
}

func main() {
	tokenPath := flag.String("token-file", "/etc/rupn/token", "File containing a RUPN connection token")
	port := flag.Int("port", 17808, "Local SOCKS5 port")
	check := flag.Bool("check", false, "Validate the connection token and exit")
	profile := flag.String("profile", "", "Connection label used in local logs")
	flag.Parse()
	if *profile != "" {
		log.SetPrefix("[" + *profile + "] ")
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, os.Interrupt)
	defer stop()
	if err := run(ctx, *tokenPath, *port, *check); err != nil {
		log.Print(err)
		os.Exit(1)
	}
}

func run(ctx context.Context, tokenPath string, port int, check bool) error {
	if port < 1 || port > 65535 {
		return errors.New("SOCKS5 port must be between 1 and 65535")
	}
	token, err := os.ReadFile(tokenPath)
	if err != nil {
		return fmt.Errorf("read connection file: %w", err)
	}
	cfg, err := parseConnection(string(token))
	if err != nil {
		return err
	}
	if check {
		return nil
	}

	mobile.SetDNS(cfg.dns)
	mobile.SetVP8Options(cfg.vp8FPS, cfg.vp8Batch)
	if err := mobile.StartWithTransport(cfg.carrier, cfg.transport, cfg.room, cfg.client, cfg.key, port, "", ""); err != nil {
		return fmt.Errorf("start RUPN tunnel: %w", err)
	}
	defer mobile.Stop()

	ready := make(chan error, 1)
	go func() { ready <- mobile.WaitReady(30000) }()
	select {
	case <-ctx.Done():
		return nil
	case err := <-ready:
		if err != nil {
			return fmt.Errorf("wait for RUPN tunnel: %w", err)
		}
	}
	log.Printf("RUPN SOCKS5 ready on 127.0.0.1:%d", port)

	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			if !mobile.IsRunning() {
				return errors.New("RUPN tunnel stopped")
			}
		}
	}
}

func connectionURI(token string) (string, error) {
	token = strings.TrimSpace(token)
	if strings.HasPrefix(token, uriPrefix) {
		return token, nil
	}

	parts := strings.Split(token, ".")
	if len(parts) != 3 || parts[0] == "" || parts[2] == "" {
		return "", errors.New("invalid RUPN token")
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return "", errors.New("invalid RUPN token payload")
	}
	var claims struct {
		URI string
	}
	if json.Unmarshal(payload, &claims) != nil || !strings.HasPrefix(claims.URI, uriPrefix) {
		return "", errors.New("RUPN token has no olcrtc connection URI")
	}
	return claims.URI, nil
}

func parseConnection(token string) (connection, error) {
	uri, err := connectionURI(token)
	if err != nil {
		return connection{}, err
	}
	carrier, rest, hasCarrier := strings.Cut(strings.TrimPrefix(uri, uriPrefix), "?")
	transport, address, hasAddress := strings.Cut(rest, "@")
	room, credentials, hasRoom := strings.Cut(address, "#")
	key, client, hasClient := strings.Cut(credentials, "%")
	client, _, _ = strings.Cut(client, "$")
	if !hasCarrier || !hasAddress || !hasRoom || !hasClient || carrier == "" || transport == "" {
		return connection{}, errors.New("incomplete olcrtc connection URI")
	}

	room, roomErr := url.PathUnescape(room)
	client, clientErr := url.PathUnescape(client)
	if roomErr != nil || clientErr != nil || room == "" || client == "" {
		return connection{}, errors.New("invalid olcrtc room or client ID")
	}
	decodedKey, err := hex.DecodeString(key)
	if err != nil || len(decodedKey) != 32 {
		return connection{}, errors.New("olcrtc encryption key must contain 32 bytes in hex")
	}

	transport, params, hasParams := strings.Cut(transport, "<")
	options := make(url.Values)
	if hasParams {
		if !strings.HasSuffix(params, ">") {
			return connection{}, errors.New("incomplete olcrtc transport options")
		}
		options, err = url.ParseQuery(strings.TrimSuffix(params, ">"))
		if err != nil {
			return connection{}, errors.New("invalid olcrtc transport options")
		}
	}
	if transport == "" {
		return connection{}, errors.New("missing olcrtc transport")
	}
	dns := options.Get("dns")
	if dns == "" {
		dns = "1.1.1.1:53"
	}
	host, port, err := net.SplitHostPort(dns)
	if err != nil || host == "" || port == "" {
		return connection{}, errors.New("olcrtc DNS must be specified as host:port")
	}
	return connection{
		carrier: carrier, transport: transport, room: room, client: client, key: key,
		dns: dns, vp8FPS: numberOption(options.Get("vp8-fps"), 60, 60),
		vp8Batch: numberOption(options.Get("vp8-batch"), 32, 64),
	}, nil
}

func numberOption(raw string, fallback, maximum int) int {
	value, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return min(max(value, 1), maximum)
}
