import os
from PIL import Image

def generate_ico():
    img = Image.open('app_icon.png')
    img.save('app_icon.ico', format='ICO', sizes=[(256, 256)])

def get_version_info():
    return """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 1, 0),
    prodvers=(1, 0, 1, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '080404b0',
        [StringStruct('CompanyName', 'ITGeeker技术奇客'),
        StringStruct('FileDescription', 'ITGeeker Stock Widget'),
        StringStruct('FileVersion', '1.0.1'),
        StringStruct('InternalName', 'GeekerStockWidget'),
        StringStruct('LegalCopyright', 'Copyright (c) 2026 ITGeeker'),
        StringStruct('OriginalFilename', 'Geeker Stock Widget.exe'),
        StringStruct('ProductName', 'Geeker Stock Widget'),
        StringStruct('ProductVersion', '1.0.1')])
      ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""

if __name__ == '__main__':
    print("Generating ICO...")
    generate_ico()
    
    print("Writing version info block...")
    with open('file_version_info.txt', 'w', encoding='utf-8') as f:
        f.write(get_version_info())
    
    print("Files ready for PyInstaller.")
