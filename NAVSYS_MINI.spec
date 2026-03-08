# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['NAVSYS\\app\\main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('NAVSYS\\ui\\templates', 'NAVSYS\\ui\\templates'), ('NAVSYS\\ui\\static', 'NAVSYS\\ui\\static')],
    hiddenimports=['flask', 'modules.navwarn_mini.process_warning', 'modules.navwarn_mini.extract_warning', 'modules.navwarn_mini.coord_preview', 'modules.astranav_mini.models', 'modules.astranav_mini.skyfield_engine', 'modules.astranav_mini.compass_error', 'modules.astranav_mini.report_nsc01', 'modules.astranav_mini.lop', 'modules.astranav_mini.report_nsc02', 'modules.portalis_mini.storage', 'modules.portalis_mini.service', 'modules.portalis_mini.crew_service', 'modules.portalis_mini.port_requirements', 'modules.portalis_mini.text_lists', 'modules.portalis_mini.document_generator', 'modules.portalis_mini.certificate_registry', 'modules.portalis_mini.certificate_checks'],
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
