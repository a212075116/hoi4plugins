#include "array64_durable_snapshot.c"
#include "array64_owner_key.h"

static int ao_stamps(void* container, const char* name, unsigned int stamps[8])
{
    char roots[6][40], key[40];
    int i;
    long long raw;
    if(!ag_name(name,roots))return 0;
    for(i=0;i<8;++i){
        as_owner_key(key,name,i);
        if(na_lookup(container,key,&raw)!=1 || raw<100000 || raw%100000 || raw/100000>2147483647LL)return 0;
        stamps[i]=(unsigned int)(raw/100000);
    }
    return 1;
}

int Array64_ExportOwned(const Array64Snapshot* snapshot, const char* scope, unsigned long long lineage,
    unsigned char* output, unsigned int capacity, unsigned int* written)
{
    unsigned int stamps[8], bytes, i;
    int result, count, gen, j;
    char roots[6][40], key[48];
    long long raw;
    if(!snapshot || !output || !written || capacity<104 || !ao_stamps(snapshot->container,snapshot->name,stamps))return -13;
    if(snapshot->magic!=0x3250414e53343641ull || snapshot->length<0 || snapshot->length>4096 ||
        !ag_name(snapshot->name,roots) || Array64Group_Read(snapshot->container,snapshot->name,-1,snapshot->generation,&raw,&count,&gen)!=2 ||
        count!=snapshot->length)return -16;
    for(i=0;i<(unsigned int)count;++i)for(j=0;j<3;++j){
        tx_element_key(key,roots[3+j],(int)i);
        if(na_lookup(snapshot->container,key,&raw)!=1 || raw!=snapshot->parts[i][j])return -16;
    }
    result=Array64_ExportBaseline(snapshot,scope,lineage,output+48,capacity-56,&bytes);
    if(result!=1)return result;
    ad_put(output,0x32304e574f343641ull,8);ad_put(output+8,1,4);ad_put(output+12,bytes,4);
    for(i=0;i<8;++i)ad_put(output+16+4*i,stamps[i],4);
    ad_put(output+48+bytes,ad_hash(output,48+bytes),8);*written=56+bytes;
    return 1;
}

int Array64_ImportOwned(void* container,const char* name,const char* scope,unsigned long long lineage,
    unsigned long long owner,const unsigned char* record,unsigned int bytes,Array64Snapshot* snapshot)
{
    unsigned int stamps[8], nested, i;
    if(!snapshot)return -1;
    snapshot->magic=0;
    if(!record || !bytes)return -10;
    if(bytes<104 || ad_get(record,8)!=0x32304e574f343641ull || ad_get(record+8,4)!=1)return -11;
    nested=(unsigned int)ad_get(record+12,4);
    if(nested<48 || nested>98452 || bytes!=56+nested || ad_get(record+bytes-8,8)!=ad_hash(record,bytes-8))return -12;
    if(!ao_stamps(container,name,stamps))return -13;
    for(i=0;i<8;++i){
        unsigned long long stored=ad_get(record+16+4*i,4);
        if(stored<1 || stored>2147483647)return -12;
        if(stored!=stamps[i])return i<4?-14:-15;
    }
    return Array64_ImportBaseline(container,name,scope,lineage,owner,record+48,nested,snapshot);
}
