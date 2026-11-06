import re, sys
p = "/usr/share/virt-manager/virtManager/vmwindow.py"
s = open(p, encoding="utf-8").read()

if "_setup_vmshield_wifi_button" in s:
    print("已经补过了"); sys.exit(0)

# 1) 在 __init__ 末尾适当位置插入初始化调用
anchor = '''        self._sync_console_page_menu_state()'''
assert anchor in s, "找不到插入锚点"
s = s.replace(anchor, '''        self._setup_vmshield_wifi_button()
''' + anchor, 1)

# 2) 追加方法定义（放到类末尾之前的最后一个方法后面）
method_anchor = '''    def _resources_sampled_cb(self'''
assert method_anchor in s, "找不到方法锚点"
new_method = '''    # ---- vmshield: 工具栏上的 VM 网络开关 ----
    def _vmshield_net(self, action):
        import subprocess
        try:
            r = subprocess.run(["sudo", "-n", "/usr/local/sbin/vmshield-net", action],
                               capture_output=True, text=True, timeout=10)
            return (r.stdout or "").strip()
        except Exception as e:  # pragma: no cover
            log.warning("vmshield helper failed: %s", e)
            return ""

    def _sync_vmshield_wifi_button(self, *args):
        btn = getattr(self, "_vmshield_wifi_btn", None)
        if btn is None:
            return True
        state = self._vmshield_net("status")
        if state == "up":
            btn.set_icon_name("network-wireless")
            btn.set_tooltip_text(_("VM 网络：已连接（点击断开）"))
        elif state == "down":
            btn.set_icon_name("network-wireless-offline")
            btn.set_tooltip_text(_("VM 网络：已断开（点击连接）"))
        else:
            btn.set_icon_name("dialog-question")
            btn.set_tooltip_text(_("VM 未运行"))
        return True

    def _on_vmshield_wifi_clicked(self, src):
        self._vmshield_net("toggle")
        self._sync_vmshield_wifi_button()

    def _setup_vmshield_wifi_button(self):
        from gi.repository import GLib
        try:
            toolbar = self.widget("details-toolbar")
            btn = Gtk.ToolButton()
            btn.set_icon_name("network-wireless")
            btn.set_tooltip_text(_("VM 网络开关"))
            btn.set_is_important(True)
            btn.connect("clicked", self._on_vmshield_wifi_clicked)
            toolbar.insert(btn, max(0, toolbar.get_n_items() - 1))
            btn.show()
            self._vmshield_wifi_btn = btn
            self._sync_vmshield_wifi_button()
            GLib.timeout_add_seconds(3, self._sync_vmshield_wifi_button)
        except Exception as e:  # pragma: no cover
            log.warning("vmshield wifi button setup failed: %s", e)

'''
s = s.replace(method_anchor, new_method + method_anchor, 1)
open(p, "w", encoding="utf-8").write(s)
print("补丁已写入")
