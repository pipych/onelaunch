import os

content = '''; OneLaunch Installer (NSIS)
!include "MUI2.nsh"
!include "nsDialogs.nsh"

Name "OneLaunch"
OutFile "..\\installer\\OneLaunch_Setup.exe"
InstallDir "$APPDATA\\OneLaunch"
RequestExecutionLevel user
Icon "..\\OneLaunch_icon.ico"
UninstallIcon "..\\OneLaunch_icon.ico"

!define MUI_ICON "..\\OneLaunch_icon.ico"
!define MUI_UNICON "..\\OneLaunch_icon.ico"

VIProductVersion "0.2.7.0"
VIAddVersionKey "CompanyName" "OneDev"
VIAddVersionKey "FileDescription" "OneLaunch Setup"
VIAddVersionKey "FileVersion" "0.2.7"
VIAddVersionKey "ProductName" "OneLaunch"
VIAddVersionKey "ProductVersion" "0.2.7"
VIAddVersionKey "LegalCopyright" "OneDev"

Var CreateDesktopShortcut
Var Dialog
Var WarnLabel

!insertmacro MUI_PAGE_LICENSE "..\\LICENSE.txt"
Page custom ShortcutPageCreate ShortcutPageLeave
Page custom WarnPageCreate
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"

Function ShortcutPageCreate
  StrCpy $CreateDesktopShortcut 1
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  ${NSD_CreateCheckbox} 0 30u 100% 12u "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u044f\u0440\u043b\u044b\u043a \u043d\u0430 \u0440\u0430\u0431\u043e\u0447\u0435\u043c \u0441\u0442\u043e\u043b\u0435"
  Pop $1
  ${NSD_SetState} $1 $CreateDesktopShortcut
  ${NSD_OnClick} $1 OnDesktopCheckboxClick
  nsDialogs::Show
FunctionEnd

Function ShortcutPageLeave
FunctionEnd

Function OnDesktopCheckboxClick
  Pop $0
  ${NSD_GetState} $0 $CreateDesktopShortcut
FunctionEnd

Function WarnPageCreate
  nsDialogs::Create 1018
  Pop $Dialog
  ${If} $Dialog == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 30u 100% 40u "\u0412\u041d\u0418\u041c\u0410\u041d\u0418\u0415: \u0432 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u043f\u0430\u043f\u043a\u0443 \u0431\u0443\u0434\u0435\u0442 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d Minecraft \u0441\u043e \u0432\u0441\u0435\u043c\u0438 \u0444\u0430\u0439\u043b\u0430\u043c\u0438 (\u043c\u043e\u0434\u044b, \u043a\u043e\u043d\u0444\u0438\u0433\u0438, Java). \u0415\u0441\u043b\u0438 \u043d\u0430 \u0434\u0438\u0441\u043a\u0435 \u043c\u0430\u043b\u043e \u0441\u0432\u043e\u0431\u043e\u0434\u043d\u043e\u0433\u043e \u043c\u0435\u0441\u0442\u0430 (\u043d\u0443\u0436\u043d\u043e \u043e\u043a\u043e\u043b\u043e 2 \u0413\u0411) \u2014 \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0440\u0443\u0433\u043e\u0439 \u0434\u0438\u0441\u043a \u043d\u0430 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u043c \u0448\u0430\u0433\u0435."
  Pop $WarnLabel
  CreateFont $0 "Segoe UI" 10 700
  SendMessage $WarnLabel ${WM_SETFONT} $0 0
  SetCtlColors $WarnLabel 0xFF6600 transparent
  ${NSD_CreateLabel} 0 85u 100% 20u "\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 \u043d\u0430 SSD \u0434\u043b\u044f \u0431\u044b\u0441\u0442\u0440\u043e\u0439 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438."
  Pop $0
  nsDialogs::Show
FunctionEnd

Section "OneLaunch" SecMain
  SetOutPath "$INSTDIR"
  File /r "..\\dist\\staging\\*"
  CreateDirectory "$SMPROGRAMS\\OneLaunch"
  CreateShortCut "$SMPROGRAMS\\OneLaunch\\OneLaunch.lnk" "$INSTDIR\\OneLaunch.exe" "" "$INSTDIR\\OneLaunch.exe" 0
  CreateShortCut "$SMPROGRAMS\\OneLaunch\\\u0423\u0434\u0430\u043b\u0438\u0442\u044c OneLaunch.lnk" "$INSTDIR\\uninstall.exe"
  ${If} $CreateDesktopShortcut == 1
    CreateShortCut "$DESKTOP\\OneLaunch.lnk" "$INSTDIR\\OneLaunch.exe" "" "$INSTDIR\\OneLaunch.exe" 0
  ${EndIf}
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  WriteRegStr HKCU "Software\\OneLaunch" "" "$INSTDIR"
  WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OneLaunch" "DisplayName" "OneLaunch"
  WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OneLaunch" "UninstallString" "$INSTDIR\\uninstall.exe"
  WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OneLaunch" "DisplayIcon" "$INSTDIR\\OneLaunch.exe"
SectionEnd

Section "uninstall"
  Delete "$INSTDIR\\*.*"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\\OneLaunch.lnk"
  Delete "$SMPROGRAMS\\OneLaunch\\*.*"
  RMDir "$SMPROGRAMS\\OneLaunch"
  DeleteRegKey HKCU "Software\\OneLaunch"
  DeleteRegKey HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OneLaunch"
SectionEnd
'''

path = r'C:\Users\pshen\.openclaw\workspace\onelaunch\installer\OneLaunch.nsi'
with open(path, 'w', encoding='cp1251') as f:
    f.write(content)

# Verify by reading back
with open(path, 'r', encoding='cp1251') as f:
    read_back = f.read()

# Check for key Russian phrases
checks = [
    '\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u044f\u0440\u043b\u044b\u043a',
    '\u0412\u041d\u0418\u041c\u0410\u041d\u0418\u0415',
    '\u0423\u0434\u0430\u043b\u0438\u0442\u044c',
    '\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f'
]
for c in checks:
    found = c in read_back
    print(f'Check "{c[:30]}..." found: {found}')

# Check for correct NSIS syntax (single brace)
found_wrong_double = '${{' in read_back
print(f'Double-brace errors: {found_wrong_double}')
found_correct = '${If}' in read_back and '${EndIf}' in read_back
print(f'Correct NSIS syntax present: {found_correct}')

print(f'File size: {os.path.getsize(path)} bytes')
print('Write OK')
