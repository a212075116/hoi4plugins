#pragma once

static inline void as_owner_key(char* key,const char* name,int i)
{
    int j=0,n=0;const char* prefix="__v64o_";
    for(j=0;j<7;++j)key[j]=prefix[j];
    while(name[n])key[j++]=name[n++];
    key[j++]='_';key[j++]=i<4?'b':'i';key[j++]=(char)('0'+i%4);key[j]=0;
}
