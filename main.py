#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文献智能总结工具
"""

import sys
import os
import asyncio

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def _bypass_proxy_for_api():
    """检测系统代理并自动绕过 API 域名，避免 VPN 导致连接失败"""
    bypass_domains = ['open.bigmodel.cn', '*.open.bigmodel.cn']

    # 方式1：设置 no_proxy 环境变量（Linux/WSL 有效）
    has_proxy = any(os.environ.get(k) for k in
                    ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY'))
    if has_proxy:
        no_proxy = os.environ.get('no_proxy', os.environ.get('NO_PROXY', ''))
        parts = [p.strip() for p in no_proxy.split(',') if p.strip()]
        for d in bypass_domains:
            if d not in parts:
                parts.append(d)
        os.environ['no_proxy'] = ','.join(parts)
        os.environ['NO_PROXY'] = ','.join(parts)

    # 方式2：检测 Windows 系统代理注册表，强制清除代理环境变量
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            winreg.CloseKey(key)
            if enabled:
                # Windows 开了系统代理，清除 Python 层面的代理设置让请求直连
                for k in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY'):
                    os.environ.pop(k, None)
        except Exception:
            pass


_bypass_proxy_for_api()

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()