#pragma once

#define CRASHPATH_MAX 1024

int  FileRedirect_Install(void);
int  FileRedirect_Installed(void);
const char* FileRedirect_GameRoot(void);
const char* FileRedirect_SourcePrefix(void);
void FileRedirect_SetEnabled(int on);
int  FileRedirect_Enabled(void);
