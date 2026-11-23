; Register only Open With candidates. Do not replace the user's default app.
!macro AtelierFileType EXT
  WriteRegStr HKCU "Software\Classes\AtelierDocs.${EXT}" "" "Atelier Docs ${EXT}"
  WriteRegStr HKCU "Software\Classes\AtelierDocs.${EXT}\DefaultIcon" "" '$\"$INSTDIR\${APP_EXECUTABLE_FILENAME}$\",0'
  WriteRegStr HKCU "Software\Classes\AtelierDocs.${EXT}\shell\open\command" "" '$\"$INSTDIR\${APP_EXECUTABLE_FILENAME}$\" $\"%1$\"'
  WriteRegNone HKCU "Software\Classes\.${EXT}\OpenWithProgids" "AtelierDocs.${EXT}"
  WriteRegStr HKCU "Software\Classes\Applications\${APP_EXECUTABLE_FILENAME}\SupportedTypes" ".${EXT}" ""
  WriteRegStr HKCU "Software\AtelierDocs\Capabilities\FileAssociations" ".${EXT}" "AtelierDocs.${EXT}"
!macroend

!macro AtelierRemoveType EXT
  DeleteRegValue HKCU "Software\Classes\.${EXT}\OpenWithProgids" "AtelierDocs.${EXT}"
  DeleteRegKey HKCU "Software\Classes\AtelierDocs.${EXT}"
!macroend

!macro AtelierTypes ACTION
  !insertmacro ${ACTION} "pdf"
  !insertmacro ${ACTION} "png"
  !insertmacro ${ACTION} "jpg"
  !insertmacro ${ACTION} "jpeg"
  !insertmacro ${ACTION} "webp"
  !insertmacro ${ACTION} "bmp"
  !insertmacro ${ACTION} "tif"
  !insertmacro ${ACTION} "tiff"
  !insertmacro ${ACTION} "gif"
  !insertmacro ${ACTION} "docx"
  !insertmacro ${ACTION} "xlsx"
  !insertmacro ${ACTION} "pptx"
  !insertmacro ${ACTION} "csv"
!macroend

!macro customInstall
  WriteRegStr HKCU "Software\Classes\Applications\${APP_EXECUTABLE_FILENAME}" "FriendlyAppName" "Atelier Docs"
  WriteRegStr HKCU "Software\Classes\Applications\${APP_EXECUTABLE_FILENAME}\shell\open\command" "" '$\"$INSTDIR\${APP_EXECUTABLE_FILENAME}$\" $\"%1$\"'
  WriteRegStr HKCU "Software\AtelierDocs\Capabilities" "ApplicationName" "Atelier Docs"
  WriteRegStr HKCU "Software\AtelierDocs\Capabilities" "ApplicationDescription" "PDF, Office ve gorsel duzenleyici"
  WriteRegStr HKCU "Software\RegisteredApplications" "Atelier Docs" "Software\AtelierDocs\Capabilities"
  !insertmacro AtelierTypes AtelierFileType
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend

!macro customUnInstall
  !insertmacro AtelierTypes AtelierRemoveType
  DeleteRegKey HKCU "Software\Classes\Applications\${APP_EXECUTABLE_FILENAME}"
  DeleteRegKey HKCU "Software\AtelierDocs\Capabilities"
  DeleteRegValue HKCU "Software\RegisteredApplications" "Atelier Docs"
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend
