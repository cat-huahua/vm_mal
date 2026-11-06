# vm_mal —— Windows 恶意样本沙箱的宿主机侧防护

给 libvirt 里的 `win11-malware` 虚拟机用的一套东西：

- **WiFi 按钮**（主要功能）：virt-manager 工具栏上的小彩色图标，一键切断/恢复 VM 网络 —— 直接打在 virt-manager 源码上，属于它的一部分
- **vmshield**（可选，默认不开）：nftables 出口白名单，VM 只能走 80/443/53/ICMP，碰不到局域网和宿主机
- **SNI/DNS 日志**（可选）：记录 VM 访问了哪些域名（tshark）
- **桌面浮窗**（可选）：不想开 virt-manager 时用的小竖条

> 本仓库**不含任何恶意样本**，只有防护/控制脚本。

## 组成

```
vmshield/
  vmshield.sh                  nftables 规则：on/off/status/watch/log/sni
  sniflog.sh                   tshark 抓 SNI / HTTP Host / DNS
  wifibtn.py                   桌面浮窗（PyQt6，28x110 竖条）
  vmshield-net                 网卡开关助手（装在 /usr/local/sbin，root 所有）
  vmshield.service             nftables 规则开机加载
  vmshield-sni.service         域名日志开机加载
  sudoers.vmshield-nettoggle   只放行 vmshield-net 的免密规则
  icons/                       按钮用的绿/红图标
virt-manager/
  patch_vmwindow.py            给 virt-manager 加工具栏按钮的补丁脚本（幂等）
  vmwindow.patch               补丁内容（对 5.1.0 生成）
docs/toolbar-after.png         打完补丁后的工具栏截图
```

## 防火墙规则（table inet vmshield）

forward 链（VM 出站）：

| 匹配 | 动作 |
|---|---|
| VM MAC → `192.168.3.0/24` | DROP（记录 `vmshield-LAN`） |
| VM MAC，已建立连接 | ACCEPT |
| VM MAC，TCP 80/443 | ACCEPT |
| VM MAC，UDP 53 | ACCEPT |
| VM MAC，ICMP | ACCEPT |
| VM MAC，其它 | DROP（记录 `vmshield-DROP`） |

input 链（VM → 宿主机）：只放行 DNS 与 DHCP，其它全 DROP（记录 `vmshield-HOST`）。

VM 是按 **MAC** 识别的，DHCP 换 IP 不影响。

## 安装

```bash
# 1) 助手脚本 + 免密
sudo install -m755 vmshield/vmshield-net /usr/local/sbin/vmshield-net
sudo install -m440 vmshield/sudoers.vmshield-nettoggle /etc/sudoers.d/vmshield-nettoggle
sudo visudo -c

# 2) 防火墙 + 日志服务
sudo install -m644 vmshield/vmshield.service vmshield/vmshield-sni.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vmshield.service vmshield-sni.service

# 3) 桌面浮窗（可选）
mkdir -p ~/.local/share/vmshield
cp vmshield/icons/*.png ~/.local/share/vmshield/
cp vmshield/wifibtn.py ~/vmshield/wifibtn.py

# 4) 图标（按钮用的绿/红 WiFi 图标）
cp -r icons/hicolor/* ~/.local/share/icons/hicolor/
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor

# 5) virt-manager 工具栏按钮
sudo cp -a /usr/share/virt-manager/virtManager/vmwindow.py /usr/share/virt-manager/virtManager/vmwindow.py.orig-vmshield
sudo python3 virt-manager/patch_vmwindow.py
sudo python3 -m py_compile /usr/share/virt-manager/virtManager/vmwindow.py
```

改 `vmshield.sh` 顶部的 `VM_MAC` / `LAN` 适配自己的虚拟机。

## 用法

```bash
sudo vmshield/vmshield.sh on|off|status
sudo vmshield/vmshield.sh watch     # tcpdump 实时看 VM 流量
sudo vmshield/vmshield.sh sni       # 实时域名日志 /var/log/vmshield-sni.log
sudo vmshield/vmshield.sh log       # 被拦截的记录
sudo /usr/local/sbin/vmshield-net on|off|toggle|status
```

virt-manager 里打开虚拟机窗口后，工具栏右侧的绿/红 WiFi 图标就是开关（每 3 秒自动同步状态）。

## 升级 virt-manager 之后

包更新会覆盖 `vmwindow.py`，按钮会消失。重新跑一次补丁即可（脚本幂等）：

```bash
sudo python3 virt-manager/patch_vmwindow.py
sudo python3 -m py_compile /usr/share/virt-manager/virtManager/vmwindow.py
```

## 逆向笔记

- [Mist bootkit 驱动分析](docs/mist-analysis.md)（@source 标注样本哈希与提取方式）

## 已知限制

- 宿主机看不到进程信息，**只能按端口放行**：样本用 443 连 C2 会被放行，和"允许 Edge"是同一件事
- ECH / DoH 会让 SNI/DNS 日志看不到域名
- 要真正断网：`virsh domif-setlink <domain> <MAC> down`
- 跑破坏性样本前请回滚到干净快照（本项目配套的快照名：`clean-after-fix`）
