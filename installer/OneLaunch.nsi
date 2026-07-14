; OneLaunch Installer (NSIS)
!include "MUI2.nsh"
!include "nsDialogs.nsh"

Name "OneLaunch"
OutFile "..\installer\OneLaunch_Setup.exe"
InstallDir "$APPDATA\OneLaunch"
RequestExecutionLevel user
Icon "..\OneLaunch_icon.ico"
UninstallIcon "..\OneLaunch_icon.ico"

!define MUI_ICON "..\OneLaunch_icon.ico"
!define MUI_UNICON "..\OneLaunch_icon.ico"

VIProductVersion "0.3.4.0"
VIAddVersionKey "CompanyName" "OneDev"
VIAddVersionKey "FileDescription" "OneLaunch Setup"
VIAddVersionKey "FileVersion" "0.3.4"
VIAddVersionKey "ProductName" "OneLaunch"
VIAddVersionKey "ProductVersion" "0.3.4"
VIAddVersionKey "LegalCopyright" "OneDev"

Var CreateDesktopShortcut
Var Dialog
Var WarnLabel

!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
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
  ${NSD_CreateCheckbox} 0 30u 100% 12u "Создать ярлык на рабочем столе"
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
  ${NSD_CreateLabel} 0 30u 100% 40u "ВНИМАНИЕ: в выбранную папку будет установлен Minecraft со всеми файлами (моды, конфиги, Java). Если на диске мало свободного места (нужно около 2 ГБ) — выберите другой диск на следующем шаге."
  Pop $WarnLabel
  CreateFont $0 "Segoe UI" 10 700
  SendMessage $WarnLabel ${WM_SETFONT} $0 0
  SetCtlColors $WarnLabel 0xFF6600 transparent
  ${NSD_CreateLabel} 0 85u 100% 20u "Рекомендуется установка на SSD для быстрой загрузки."
  Pop $0
  nsDialogs::Show
FunctionEnd

Section "OneLaunch" SecMain
  SetOutPath "$INSTDIR"
  File /r "..\dist\staging\*"
  CreateDirectory "$SMPROGRAMS\OneLaunch"
  CreateShortCut "$SMPROGRAMS\OneLaunch\OneLaunch.lnk" "$INSTDIR\OneLaunch.exe" "" "$INSTDIR\OneLaunch.exe" 0
  CreateShortCut "$SMPROGRAMS\OneLaunch\Удалить OneLaunch.lnk" "$INSTDIR\uninstall.exe"
  ${If} $CreateDesktopShortcut == 1
    CreateShortCut "$DESKTOP\OneLaunch.lnk" "$INSTDIR\OneLaunch.exe" "" "$INSTDIR\OneLaunch.exe" 0
  ${EndIf}
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\OneLaunch" "" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\OneLaunch" "DisplayName" "OneLaunch"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\OneLaunch" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\OneLaunch" "DisplayIcon" "$INSTDIR\OneLaunch.exe"
SectionEnd

Section "uninstall"
  Delete "$INSTDIR\*.*"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\OneLaunch.lnk"
  Delete "$SMPROGRAMS\OneLaunch\*.*"
  RMDir "$SMPROGRAMS\OneLaunch"
  DeleteRegKey HKCU "Software\OneLaunch"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\OneLaunch"
SectionEnd
