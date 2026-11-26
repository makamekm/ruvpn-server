'use strict';
'require view';
'require rpc';
'require poll';
'require ui';

function method(name, params) {
    return rpc.declare({ object: 'luci.rupn', method: name, params, expect: { '': {} }, reject: true });
}

const getStatus = method('status', []);
const getLogs = method('logs', ['id']);
const probe = method('probe', ['id']);
const manage = method('manage', ['id', 'action']);
const saveProfile = method('save_profile', ['id', 'name', 'token', 'enabled']);

const messages = {
    busy: _('Другая операция RUPN ещё выполняется.'),
    invalid_name: _('Укажите имя подключения длиной до 64 символов.'),
    missing_token: _('Вставьте ключ RUPN.'),
    invalid_token: _('Ключ не прошёл проверку формата.'),
    no_ports: _('Нет свободных портов для нового подключения.'),
    invalid_profile: _('Подключение не найдено.'),
    save_failed: _('Не удалось сохранить подключение.'),
    service_failed: _('Команда службы RUPN завершилась ошибкой.'),
    used_by_podkop: _('Это подключение выбрано в Podkop. Сначала переключите соответствующую секцию.'),
    socks_unavailable: _('Локальный SOCKS5 ещё не доступен.'),
    probe_failed: _('Через SOCKS5 не удалось открыть example.com.')
};

function button(label, style, handler) {
    return E('button', { type: 'button', class: 'cbi-button ' + style, click: handler }, label);
}

function field(label, input) {
    return E('div', { class: 'cbi-value' }, [
        E('label', { for: input.id, class: 'cbi-value-title' }, label),
        E('div', { class: 'cbi-value-field' }, input)
    ]);
}

return view.extend({
    load: getStatus,

    render(initial) {
        const writable = L.hasViewPermission();
        let state = initial;
        let editing = '';
        let selectedLog = null;
        let busy = false;

        const profiles = E('div');
        const editTitle = E('h3');
        const name = E('input', {
            id: 'rupn-profile-name', class: 'cbi-input-text', maxlength: 64,
            style: 'width: 100%; max-width: 32rem', placeholder: _('Например, Дом или Сервер 2')
        });
        const token = E('input', {
            id: 'rupn-profile-key', class: 'cbi-input-password', type: 'password',
            autocomplete: 'new-password', maxlength: 8192, spellcheck: 'false',
            style: 'width: 100%; max-width: 32rem'
        });
        const enabled = E('input', { id: 'rupn-profile-enabled', type: 'checkbox', checked: true });
        const enabledField = field(_('Запустить сразу'), enabled);
        const boot = E('span');
        const domains = E('span', { style: 'white-space: pre-wrap' });
        const feedback = E('span', { role: 'status', 'aria-live': 'polite' });
        const logTitle = E('h3');
        const logText = E('pre', { style: 'max-height: 28rem; overflow: auto; white-space: pre-wrap;' });
        const logPanel = E('div', { class: 'cbi-section', hidden: true });

        function refreshForm() {
            editTitle.textContent = editing ? _('Изменить подключение') : _('Добавить подключение');
            token.placeholder = editing ? _('Вставьте новый ключ, если хотите его заменить') : _('Вставьте ключ RUPN сюда');
            submit.textContent = editing ? _('Сохранить подключение') : _('Добавить подключение');
            enabledField.hidden = Boolean(editing);
            cancel.hidden = !editing;
            name.disabled = token.disabled = enabled.disabled = !writable || busy;
            submit.disabled = !writable || busy;
        }

        function edit(profile) {
            editing = profile ? profile.id : '';
            name.value = profile ? profile.name : '';
            token.value = '';
            enabled.checked = true;
            refreshForm();
            if (profile)
                name.focus();
        }

        function update(data) {
            state = data;
            boot.textContent = data.autostart ? _('Автозапуск включён') : _('Автозапуск выключен');
            bootButton.textContent = data.autostart ? _('Выключить автозапуск') : _('Включить автозапуск');
            bootButton.disabled = !writable || busy;
            domains.textContent = data.domains || '—';
            profiles.replaceChildren(...data.profiles.map(profile => {
                const status = profile.ready ? _('SOCKS5 готов') :
                    profile.enabled ? _('Ожидает запуска') : _('Остановлен');
                const info = '127.0.0.1:' + profile.port + ' · ' + status +
                    (profile.pid ? ' · PID ' + profile.pid : '');
                const toggle = button(profile.enabled ? _('Остановить') : _('Запустить'), 'cbi-button-action',
                    () => perform(() => manage(profile.id, profile.enabled ? 'stop' : 'start')));
                const restart = button(_('Перезапустить'), 'cbi-button-action',
                    () => perform(() => manage(profile.id, 'restart')));
                const settings = button(_('Изменить'), 'cbi-button-action', () => edit(profile));
                const remove = button(_('Удалить'), 'cbi-button-negative', () => {
                    if (window.confirm(_('Удалить подключение и его ключ?')))
                        perform(() => manage(profile.id, 'delete'), () => {
                            if (editing === profile.id) edit(null);
                            if (selectedLog?.id === profile.id) {
                                selectedLog = null;
                                logPanel.hidden = true;
                            }
                        });
                });
                const test = button(_('Проверить'), 'cbi-button-action', () => perform(() => probe(profile.id), data => {
                    feedback.textContent = profile.name + ' · HTTP ' + data.code + ' · ' + data.seconds.toFixed(2) + ' ' + _('с');
                }));
                const journal = button(_('Журнал'), 'cbi-button-action', () => showLogs(profile));
                toggle.disabled = settings.disabled = remove.disabled = !writable || busy;
                restart.disabled = !writable || busy || !profile.enabled;
                test.disabled = busy || !profile.ready;
                return E('div', { class: 'cbi-section-node' }, [
                    E('h4', profile.name),
                    E('p', info),
                    E('p', [toggle, ' ', restart, ' ', settings, ' ', test, ' ', journal, ' ', remove])
                ]);
            }));
            if (!data.profiles.length)
                profiles.appendChild(E('p', _('Подключений пока нет. Добавьте первое через форму выше.')));
            refreshForm();
        }

        async function perform(operation, onSuccess) {
            busy = true;
            feedback.textContent = '';
            update(state);
            try {
                const result = await operation();
                if (!result.ok)
                    throw new Error(messages[result.error] || _('Операция RUPN завершилась ошибкой.'));
                if (onSuccess)
                    onSuccess(result);
            } catch (error) {
                ui.addNotification(null, E('p', error.message || _('RUPN недоступен.')), 'error');
            } finally {
                busy = false;
                update(state);
                getStatus().then(update).catch(() => {});
            }
        }

        async function showLogs(profile) {
            selectedLog = profile;
            logPanel.hidden = false;
            logTitle.textContent = _('Журнал') + ' · ' + profile.name;
            logText.textContent = _('Загрузка журнала…');
            try {
                const result = await getLogs(profile.id);
                if (selectedLog?.id === profile.id)
                    logText.textContent = result.ok ? (result.text || _('Записей пока нет.')) : _('Журнал недоступен.');
            } catch {
                if (selectedLog?.id === profile.id)
                    logText.textContent = _('Не удалось получить журнал.');
            }
        }

        const submit = button('', 'cbi-button-apply', () => {
            const label = name.value.trim();
            const key = token.value.trim();
            if (!label || (!editing && !key)) {
                ui.addNotification(null, E('p', !label ? messages.invalid_name : messages.missing_token), 'error');
                (!label ? name : token).focus();
                return;
            }
            perform(() => saveProfile(editing, label, key, enabled.checked ? 1 : 0), () => {
                edit(null);
                ui.addNotification(null, E('p', _('Подключение сохранено.')), 'info');
            });
        });
        const cancel = button(_('Отмена'), 'cbi-button-reset', () => edit(null));
        const bootButton = button('', 'cbi-button-action', () =>
            perform(() => manage('', state.autostart ? 'disable_boot' : 'enable_boot')));
        const refreshLog = button(_('Обновить журнал'), 'cbi-button-action', () => {
            if (selectedLog)
                showLogs(selectedLog);
        });
        logPanel.append(logTitle, E('p', refreshLog), logText);
        update(initial);
        poll.add(() => getStatus().then(data => {
            if (!busy && JSON.stringify(state) !== JSON.stringify(data))
                update(data);
        }), 5);

        return E('div', [
            E('h2', 'RUPN'),
            E('div', { class: 'cbi-section' }, [
                editTitle,
                field(_('Имя подключения'), name),
                field(_('Ключ RUPN (JWT или olcrtc://)'), token),
                enabledField,
                E('p', [submit, ' ', cancel])
            ]),
            E('div', { class: 'cbi-section' }, [
                E('h3', _('Подключения')),
                E('p', [boot, ' · ', bootButton]),
                E('p', [_('Домены текущей секции RUPN'), ' · ', domains, ' · ',
                    E('a', { href: L.url('admin', 'services', 'podkop') }, 'Podkop')]),
                E('p', feedback),
                profiles
            ]),
            logPanel
        ]);
    },

    handleSaveApply: null,
    handleSave: null,
    handleReset: null
});
