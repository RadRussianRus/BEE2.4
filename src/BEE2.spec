import shutil
import os
import io
import srctools
from zipfile import ZipFile

ico_path = os.path.realpath(os.path.join(os.getcwd(), "../bee2.ico"))


# src -> build subfolder.
data_files = [
    ('../README.md', '.'),
    ('../BEE2.ico', '.'),
    ('../BEE2.fgd', '.'),
    ('../images/BEE2/*.png', 'images/BEE2/'),
    ('../images/icons/*.png', 'images/icons/'),
    ('../images/splash_screen/*.jpg', 'images/splash_screen/'),
    ('../palettes/*.bee2_palette', 'palettes/'),

    # Add the FGD data for us.
    (os.path.join(srctools.__path__[0], 'fgd.lzma'), 'srctools'),
    (os.path.join(srctools.__path__[0], 'srctools.fgd'), 'srctools'),

]

def get_localisation(key):
    """Get localisation files from Loco."""
    import requests

    # Make the directories.
    os.makedirs('../i18n/', exist_ok=True)

    print('Reading translations... ', end='', flush=True)
    zip_request = requests.get(
        'https://localise.biz/api/export/archive/mo.zip',
        headers={
            'Authorization': 'Loco ' + key,
        },
        params={
            'path': '{%lang}{_%region}.{%ext}',
        },
    )
    zip_file = ZipFile(io.BytesIO(zip_request.content))
    print('Done!')

    print('Translations: ')

    for file in zip_file.infolist():  # type: ZipInfo
        if 'README.txt' in file.filename:
            continue
        filename = os.path.basename(file.filename)
        print(filename)
        # Copy to the dev and output directory.
        with zip_file.open(file) as src, open('../i18n/' + filename, 'wb') as dest:
            shutil.copyfileobj(src, dest)
            data_files.append((dest.name, 'i18n'))

# get_localisation('kV-oMlhZPJEJoYPI5EQ6HaqeAc1zQ73G')


block_cipher = None


# AVbin is needed to read OGG files.
INCLUDE_LIBS = [
    'C:/Windows/system32/avbin.dll',  # Win 32 bit
    'C:/Windows/sysWOW64/avbin64.dll',  # Win 64 bit
    'libavbin.dylib',  # OS X - must be relative.
    '/usr/lib/libavbin.so',  # Linux
]

# Filter out files for other platforms
INCLUDE_LIBS = [
    (path, '.') for path in INCLUDE_LIBS
    if os.path.exists(path)
]

bee_version = input('BEE2 Version: ')

# Write this to the temp folder, so it's picked up and included.
with open(os.path.join(workpath, 'BUILD_CONSTANTS.py'), 'w') as f:
    f.write('BEE_VERSION=' + repr(bee_version))

for snd in os.listdir('sounds/'):
    if snd == 'music_samp':
        continue
    data_files.append(('../sounds/' + snd, 'sounds'))


# We need to include this version data.
try:
    import importlib_resources
    data_files.append(
        (
            os.path.join(importlib_resources.__path__[0], 'version.txt'),
            'importlib_resources',
         )
    )
except ImportError:
    pass

print('Data files: ')
print(data_files)



# Finally, run the PyInstaller analysis process.

bee2_a = Analysis(
    ['BEE2_launch.pyw'],
    pathex=[workpath, os.path.dirname(srctools.__path__[0])],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    bee2_a.pure,
    bee2_a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    bee2_a.scripts,
    [],
    exclude_binaries=True,
    name='BEE2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='BEE2.ico'
)

coll = COLLECT(
    exe,
    bee2_a.binaries,
    bee2_a.zipfiles,
    bee2_a.datas,
    strip=False,
    upx=True,
    name='BEE2',
)
