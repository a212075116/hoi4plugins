#include "array64_shape_transaction.c"

typedef struct {
    Array64Snapshot baseline;
    unsigned int stamps[8],nonce[4];
    int op,index,old_length,old_generation,target_length,wide,size;
    long long raw;
} Array64Journal;

unsigned int Array64_JournalBytes(void){return (unsigned int)sizeof(Array64Journal);}

static void aj_key(char* key,const char* name,int i)
{
    int n=0,j;const char* prefix="__v64t_";
    for(j=0;j<7;++j)key[j]=prefix[j];while(name[n])key[j++]=name[n++];
    key[j++]='_';key[j++]=i<4?'n':'p';if(i<4)key[j++]=(char)('0'+i);key[j]=0;
}

static int aj_target(int op,int index,int old,int size)
{
    if(op==0)return old==-1&&index==0?size:-2;
    if(old<0)return -2;
    if(op==1)return old<4096?old+1:-2;
    if(op==2)return old<4096&&index>=0&&index<=old?old+1:-2;
    if(op==3)return index>=0&&index<old?old-1:-2;
    if(op==4)return -1;
    if(op==5)return size;
    if(op==6)return index>=0&&index<old?old:-2;
    return -2;
}

static int aj_absent(void* c,const char* name)
{
    char roots[6][40];int count;
    for(int i=0;i<6;++i)aj_key(roots[i],name,i<5?i:4);
    return ag_inventory(c,roots,&count)&&count==0;
}

static int aj_i32(const unsigned char* p)
{
    unsigned int v=(unsigned int)ad_get(p,4);
    return v<=2147483647u?(int)v:-1-(int)(~v);
}

int Array64_JournalPrepare(void* c,const char* name,const char* scope,unsigned long long lineage,int op,int index,
    int expected_gen,long long raw,int wide,int size,const unsigned int* fresh_stamps,const unsigned int* nonce,
    unsigned char* output,unsigned int capacity,unsigned int* written,Array64Journal* scratch)
{
    Array64Snapshot* snapshot;unsigned int stamps[8],nested=0,pos,total,n=0;char roots[6][40];
    int sl=ad_scope(scope),old=-1,gen=0,target,count;long long value,encoded[3];
    if(!scratch||!output||!written||!nonce||!lineage||!sl||!ag_name(name,roots)||op<0||op>6||size<0||size>4096||
        !as_encode(raw,wide,encoded)||!aj_absent(c,name))return -1;
    snapshot=&scratch->baseline;
    for(int i=0;i<4;++i)if(!nonce[i]||nonce[i]>2147483647u)return -1;
    while(name[n])++n;
    if(op==0){
        if(expected_gen!=0||!fresh_stamps||!ag_inventory(c,roots,&count)||count||!as_owner_absent(c,name))return -2;
        for(int i=0;i<8;++i){if(!fresh_stamps[i]||fresh_stamps[i]>2147483647u)return -1;stamps[i]=fresh_stamps[i];}
    }else{
        if(Array64Group_Read(c,name,-1,expected_gen,&value,&old,&gen)!=2||gen>2147483644||!ao_stamps(c,name,stamps)||
            Array64_Capture(c,name,gen,42,snapshot)!=1)return -2;
    }
    target=aj_target(op,index,old,size);if(target<-1)return -1;
    pos=120+(unsigned int)sl+n;if(capacity<pos+8)return -3;
    if(op!=0&&Array64_ExportOwned(snapshot,scope,lineage,output+pos,capacity-pos-8,&nested)!=1)return -3;
    total=pos+nested+8;
    ad_put(output,0x32304e524a343641ull,8);ad_put(output+8,1,4);ad_put(output+12,(unsigned int)op,4);
    ad_put(output+16,(unsigned int)index,4);ad_put(output+20,(unsigned int)old,4);ad_put(output+24,(unsigned int)gen,4);
    ad_put(output+28,(unsigned int)target,4);ad_put(output+32,(unsigned long long)raw,8);ad_put(output+40,(unsigned int)wide,4);
    ad_put(output+44,(unsigned int)size,4);ad_put(output+48,lineage,8);
    for(int i=0;i<8;++i)ad_put(output+56+4*i,stamps[i],4);
    for(int i=0;i<4;++i)ad_put(output+88+4*i,nonce[i],4);
    ad_put(output+104,(unsigned int)sl,4);ad_put(output+108,n,4);ad_put(output+112,nested,4);ad_put(output+116,0,4);
    for(int i=0;i<sl;++i)output[120+i]=(unsigned char)scope[i];
    for(unsigned int i=0;i<n;++i)output[120+sl+i]=(unsigned char)name[i];
    ad_put(output+total-8,ad_hash(output,total-8),8);*written=total;return 1;
}

static int aj_parse(void* c,const char* name,const char* scope,unsigned long long lineage,
    const unsigned char* record,unsigned int bytes,Array64Journal* j)
{
    unsigned int sl,n,nested,pos;char roots[6][40];long long encoded[3];
    if(!record||!j||bytes<130||!ad_scope(scope)||!ag_name(name,roots))return -1;
    if(ad_get(record,8)!=0x32304e524a343641ull||ad_get(record+8,4)!=1||ad_get(record+116,4)!=0)return -2;
    sl=(unsigned int)ad_get(record+104,4);n=(unsigned int)ad_get(record+108,4);nested=(unsigned int)ad_get(record+112,4);
    if(!sl||sl>80||!n||n>20||nested>98508||bytes!=128+sl+n+nested||ad_get(record+bytes-8,8)!=ad_hash(record,bytes-8))return -2;
    if(ad_get(record+48,8)!=lineage||!lineage)return -3;
    for(unsigned int i=0;i<sl;++i)if(!record[120+i]||record[120+i]!=(unsigned char)scope[i])return -3;
    if(scope[sl])return -3;
    for(unsigned int i=0;i<n;++i)if(!record[120+sl+i]||record[120+sl+i]!=(unsigned char)name[i])return -3;
    if(name[n])return -3;
    j->op=aj_i32(record+12);j->index=aj_i32(record+16);j->old_length=aj_i32(record+20);j->old_generation=aj_i32(record+24);
    j->target_length=aj_i32(record+28);j->wide=aj_i32(record+40);j->size=aj_i32(record+44);
    {unsigned long long bits=ad_get(record+32,8);j->raw=bits<=9223372036854775807ull?(long long)bits:-1-(long long)(~bits);}
    if(j->op<0||j->op>6||j->old_length<-1||j->old_length>4096||j->old_generation<0||j->old_generation>2147483644||
        j->old_generation%2||j->size<0||j->size>4096||!as_encode(j->raw,j->wide,encoded)||
        aj_target(j->op,j->index,j->old_length,j->size)!=j->target_length||j->target_length<-1||j->target_length>4096)return -2;
    for(int i=0;i<8;++i){j->stamps[i]=(unsigned int)ad_get(record+56+4*i,4);if(!j->stamps[i]||j->stamps[i]>2147483647u)return -2;}
    for(int i=0;i<4;++i){j->nonce[i]=(unsigned int)ad_get(record+88+4*i,4);if(!j->nonce[i]||j->nonce[i]>2147483647u)return -2;}
    j->baseline.magic=0;j->baseline.container=c;j->baseline.owner=42;j->baseline.generation=j->old_generation;
    j->baseline.length=j->old_length;j->baseline.consumed=0;
    for(int i=0;i<21;++i)j->baseline.name[i]=(unsigned int)i<n?name[i]:0;
    if(j->op==0)return j->old_length==-1&&j->old_generation==0&&nested==0?1:-2;
    pos=120+sl+n;
    {const unsigned char* owned=record+pos;unsigned int bsize;const unsigned char* base;
    if(nested<104||ad_get(owned,8)!=0x32304e574f343641ull||ad_get(owned+8,4)!=1||ad_get(owned+nested-8,8)!=ad_hash(owned,nested-8))return -2;
    bsize=(unsigned int)ad_get(owned+12,4);if(bsize+56!=nested)return -2;
    for(int i=0;i<8;++i)if(ad_get(owned+16+4*i,4)!=j->stamps[i])return -2;
    base=owned+48;
    if(bsize!=48+sl+n+24*(unsigned int)j->old_length||ad_get(base,8)!=0x3245534142343641ull||ad_get(base+8,4)!=1||ad_get(base+12,4)!=2||
        aj_i32(base+16)!=j->old_length||aj_i32(base+20)!=j->old_generation||ad_get(base+24,8)!=lineage||ad_get(base+32,4)!=sl||ad_get(base+36,4)!=n||
        ad_get(base+bsize-8,8)!=ad_hash(base,bsize-8))return -2;
    for(unsigned int i=0;i<sl+n;++i)if(base[40+i]!=record[120+i])return -2;
    pos=40+sl+n;
    for(int i=0;i<j->old_length;++i)for(int k=0;k<3;++k){unsigned long long bits=ad_get(base+pos,8);pos+=8;
        j->baseline.parts[i][k]=bits<=9223372036854775807ull?(long long)bits:-1-(long long)(~bits);}
    for(int i=0;i<j->old_length;++i)if(!ar_valid_parts(j->baseline.parts[i]))return -2;
    }
    j->baseline.checksum=ar_hash(&j->baseline);j->baseline.magic=0x3250414e53343641ull;return 1;
}

static int aj_receipt(void* c,const char* name,const unsigned int nonce[4])
{
    char key[40];long long value;
    for(int i=0;i<5;++i){aj_key(key,name,i);if(na_lookup(c,key,&value)!=1||value!=(i<4?nonce[i]*100000LL:100000LL))return 0;}
    return 1;
}

static int aj_current_keys(void* c,const char* name,char data[6][40],int maximum)
{
    char roots[19][40],text[128];unsigned int lengths[19],mask,span,offset,take,i,k;unsigned char spill,block[1536];
    const unsigned char* table;
    for(i=0;i<6;++i){k=0;while((roots[i][k]=data[i][k])!=0)++k;}
    for(i=0;i<8;++i)as_owner_key(roots[6+i],name,(int)i);
    for(i=0;i<5;++i)aj_key(roots[14+i],name,(int)i);
    for(i=0;i<19;++i){lengths[i]=0;while(roots[i][lengths[i]])++lengths[i];}
    if(!na_read_memory((unsigned char*)c+24,&table,8)||!na_read_memory((unsigned char*)c+36,&mask,4)||
        !na_read_memory((unsigned char*)c+40,&spill,1)||!table||mask<1||mask>1048575u||(mask&(mask+1)))return 0;
    span=mask+1+spill;
    for(offset=0;offset<span;offset+=take){
        take=span-offset;if(take>32)take=32;
        if(!na_read_memory(table+48ull*offset,block,48ull*take))return 0;
        for(unsigned int slot=0;slot<take;++slot){
            unsigned char* node=block+48*slot;NaSize size,cap;if(!node[4])continue;
            size=*(NaSize*)(node+24);cap=*(NaSize*)(node+32);
            if(!size||size>=128||size>cap||(cap<=15&&size>15))return 0;
            if(cap<=15){for(k=0;k<size;++k)text[k]=(char)node[8+k];}
            else if(!na_read_memory(*(const char**)(node+8),text,size))return 0;
            for(k=0;k<size;++k)if(!text[k])return 0;
            text[size]=0;
            for(i=0;i<19;++i){
                for(k=0;k<lengths[i]&&text[k]==roots[i][k];++k){}
                if(k!=lengths[i]||(text[k]&&text[k]!='^'))continue;
                if(i<3||i>=6){if(text[k])return 0;break;}
                if(text[k]!='^')return 0;
                if(text[k+1]=='n'&&text[k+2]=='u'&&text[k+3]=='m'&&!text[k+4])break;
                ++k;unsigned int index=0,digits=0;
                while(text[k]){if(text[k]<'0'||text[k]>'9'||digits>=4||(!digits&&text[k]=='0'&&text[k+1]))return 0;
                    index=index*10+(text[k]-'0');++k;++digits;}
                if(!digits||index>=(unsigned int)(maximum<0?0:maximum))return 0;
                break;
            }
        }
    }
    return 1;
}

int Array64_JournalBegin(void* c,const char* name,const char* scope,unsigned long long lineage,
    const unsigned char* record,unsigned int bytes,Array64Journal* j)
{
    char roots[6][40],key[40];int count,step=0;
    if(aj_parse(c,name,scope,lineage,record,bytes,j)!=1||!ag_name(name,roots)||!aj_absent(c,name))return -1;
    if(j->op==0){if(!ag_inventory(c,roots,&count)||count||!as_owner_absent(c,name))return -3;}
    else if(!as_matches(c,name,roots,j->baseline.parts,j->old_length,j->old_generation,j->stamps))return -3;
    for(int i=0;i<5;++i){aj_key(key,name,i);if(!as_put(c,key,i<4?j->nonce[i]*100000LL:100000LL,&step,0))return -4;}
    return 1;
}

int Array64_JournalRecover(void* c,const char* name,const char* scope,unsigned long long lineage,
    const unsigned char* record,unsigned int bytes,Array64Journal* j,int fail_stage)
{
    char roots[6][40],key[48];long long raw;int step=0,maximum,ok;
    if(aj_parse(c,name,scope,lineage,record,bytes,j)!=1||!ag_name(name,roots)||fail_stage<0)return -1;
    if(!aj_receipt(c,name,j->nonce))return -5;
    if(na_lookup(c,roots[1],&raw)!=1||raw!=(j->old_generation+1LL)*100000)return -6;
    for(int i=0;i<8;++i){as_owner_key(key,name,i);int found=na_lookup(c,key,&raw);
        if(found<0||(found==1&&raw!=j->stamps[i]*100000LL))return -7;}
    maximum=j->old_length>j->target_length?j->old_length:j->target_length;
    if(!aj_current_keys(c,name,roots,maximum))return -7;
    if(!as_native_put(c,roots[1],(j->old_generation+1LL)*100000))return -4;
    ok=as_install(c,name,roots,j->baseline.parts,j->old_length,maximum<0?0:maximum,j->stamps,&step,fail_stage);
    if(!ok){if(!as_native_put(c,roots[1],(j->old_generation+1LL)*100000))return -4;return -3;}
    ok=j->op==0?as_erase(c,roots[1],&step,fail_stage):as_put(c,roots[1],(j->old_generation+2LL)*100000,&step,fail_stage);
    if(!ok){if(!as_native_put(c,roots[1],(j->old_generation+1LL)*100000))return -4;return -3;}
    if(!as_matches(c,name,roots,j->baseline.parts,j->old_length,j->old_generation+2,j->stamps)){
        if(!as_native_put(c,roots[1],(j->old_generation+1LL)*100000))return -4;return -3;
    }
    for(int i=0;i<5;++i){aj_key(key,name,i);if(!as_erase(c,key,&step,fail_stage))return -4;}
    return 1;
}

int Array64_JournalFinish(void* c,const char* name,const char* scope,unsigned long long lineage,
    const unsigned char* record,unsigned int bytes,Array64Journal* j,int mode)
{
    char roots[6][40],key[48];long long raw,encoded[3];unsigned int stamps[8];int length,gen,found=0,step=0,count,g;
    if(aj_parse(c,name,scope,lineage,record,bytes,j)!=1||!ag_name(name,roots)||mode<1||mode>3)return -1;
    length=mode==1?j->target_length:j->old_length;gen=j->old_generation+(mode==3?0:2);
    if(length<0){if(!as_matches(c,name,roots,j->baseline.parts,-1,gen,j->stamps))return -6;}
    else{
        if(Array64Group_Read(c,name,-1,gen,&raw,&count,&g)!=2||count!=length||!ao_stamps(c,name,stamps))return -6;
        for(int i=0;i<8;++i)if(stamps[i]!=j->stamps[i])return -7;
        if(!as_encode(j->raw,j->wide,encoded))return -1;
        for(int i=0;i<length;++i)for(int k=0;k<3;++k){
            long long expected;
            if(mode!=1)expected=j->baseline.parts[i][k];
            else if(j->op==0||(j->op==1&&i==j->old_length)||(j->op==2&&i==j->index)||(j->op==5&&i>=j->old_length)||(j->op==6&&i==j->index))expected=encoded[k];
            else {int oldindex=i;if(j->op==2&&i>j->index)--oldindex;if(j->op==3&&i>=j->index)++oldindex;expected=j->baseline.parts[oldindex][k];}
            tx_element_key(key,roots[3+k],i);if(na_lookup(c,key,&raw)!=1||raw!=expected)return -6;
        }
    }
    for(int i=0;i<5;++i){aj_key(key,name,i);int exists=na_lookup(c,key,&raw);if(exists<0)return -7;
        if(exists){++found;if(raw!=(i<4?j->nonce[i]*100000LL:100000LL))return -5;}}
    if(!found)return 2;
    for(int i=0;i<5;++i){aj_key(key,name,i);if(!as_erase(c,key,&step,0))return -4;}
    return 1;
}

int Array64_JournalApply(void* c,const char* name,const char* scope,unsigned long long lineage,
    const unsigned char* record,unsigned int bytes,Array64Journal* j,Array64ShapeWork* work,int fail_stage,int fail_compensation)
{
    int result;
    if(aj_parse(c,name,scope,lineage,record,bytes,j)!=1||!aj_receipt(c,name,j->nonce))return -1;
    result=Array64_ShapeApply(c,name,j->op,j->index,j->old_generation,j->raw,j->wide,j->size,j->stamps,work,fail_stage,fail_compensation);
    if(result==1||result==2){int final=Array64_JournalFinish(c,name,scope,lineage,record,bytes,j,result==1?1:3);if(final<0)return -4;}
    return result;
}
