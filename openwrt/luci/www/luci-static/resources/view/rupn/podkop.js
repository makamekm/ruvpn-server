'use strict';
'require baseclass';
'require form';
'require rpc';

const status = rpc.declare({
    object: 'luci.rupn', method: 'status', expect: { '': { profiles: [] } }, reject: true
});
let available;

return baseclass.extend({
    addConnectionPicker(section) {
        const picker = section.option(form.ListValue, '_rupn_connection',
            _('Подключение RUPN'), _('Выберите подключение по имени. Podkop подставит его локальный SOCKS5 в URL прокси.'));
        picker.depends({ connection_type: 'proxy', proxy_config_type: 'url' });
        picker.value('', _('Ввести URL вручную'));
        picker.load = function(sectionId) {
            available ??= status().catch(() => ({ profiles: [] }));
            return available.then(data => {
                const selected = this.map.data.get(this.map.config, sectionId, 'proxy_string');
                let match = '';
                for (const profile of data.profiles || []) {
                    const url = 'socks5://127.0.0.1:' + profile.port;
                    if (!this.keylist.includes(url))
                        this.value(url, profile.name + (profile.enabled ? '' : ' · ' + _('остановлено')));
                    if (url === selected)
                        match = url;
                }
                return match;
            });
        };
        picker.onchange = function(ev, sectionId, value) {
            const input = section.getUIElement(sectionId, 'proxy_string');
            if (input && value)
                input.setValue(value);
        };
        picker.write = picker.remove = function() {};
    }
});
