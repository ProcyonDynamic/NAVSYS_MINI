# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['NAVSYS\\app\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('NAVSYS\\modules\\navwarn_mini\\semantic_registry', 'NAVSYS\\modules\\navwarn_mini\\semantic_registry'), ('NAVSYS\\modules\\navwarn_mini\\plot_policy_defaults.json', 'NAVSYS\\modules\\navwarn_mini')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NAVSYS_MINI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NAVSYS_MINI',
)
