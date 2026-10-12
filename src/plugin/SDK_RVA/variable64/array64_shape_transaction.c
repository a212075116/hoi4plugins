#include "array64_ownership_gate.c"

extern int as_native_put(void* container,const char* key,long long raw);
extern int as_native_erase(void* container,const char* key);

typedef struct {
    Array64Snapshot baseline;
    long long next[4096][3];
    unsigned int stamps[8];
    int old_length,new_length,old_generation,absent;
} Array64ShapeWork;

unsigned int Array64_ShapeBytes(void){return (unsigned int)sizeof(Array64ShapeWork);}

static void as_owner_key(char* key,const char* name,int i)
{
    int j=0,n=0;const char* prefix="__v64o_";
    for(j=0;j<7;++j)key[j]=prefix[j];
    while(name[n])key[j++]=name[n++];
    key[j++]='_';key[j++]=i<4?'b':'i';key[j++]=(char)('0'+i%4);key[j]=0;
}

static int as_put(void* c,const char* key,long long raw,int* step,int fail)
{
    long long value;
    if(++*step==fail)return 0;
    return as_native_put(c,key,raw)&&na_lookup(c,key,&value)==1&&value==raw;
}

static int as_erase(void* c,const char* key,int* step,int fail)
{
    long long raw;int found=na_lookup(c,key,&raw);
    if(++*step==fail || found<0)return 0;
    if(!found)return 1;
    return as_native_erase(c,key)&&na_lookup(c,key,&raw)==0;
}

static int as_owner_absent(void* c,const char* name)
{
    char keys[6][40];int owned;
    for(int i=0;i<6;++i)as_owner_key(keys[i],name,i);
    if(!ag_inventory(c,keys,&owned)||owned)return 0;
    for(int i=0;i<6;++i)as_owner_key(keys[i],name,6+i%2);
    if(!ag_inventory(c,keys,&owned)||owned)return 0;
    return 1;
}

static void as_length_key(char* key,const char* root)
{
    int n=0;while(root[n]){key[n]=root[n];++n;}
    key[n++]='^';key[n++]='n';key[n++]='u';key[n++]='m';key[n]=0;
}

static int as_install(void* c,const char* name,char roots[6][40],long long parts[4096][3],
    int length,int previous,const unsigned int stamps[8],int* step,int fail)
{
    char key[48];int ok=1,i,j;
    if(length>=0){
        for(i=0;i<8;++i){as_owner_key(key,name,i);if(!as_put(c,key,stamps[i]*100000LL,step,fail))ok=0;}
        if(!as_put(c,roots[0],200000,step,fail))ok=0;
        for(i=0;i<length;++i)for(j=0;j<3;++j){tx_element_key(key,roots[3+j],i);if(!as_put(c,key,parts[i][j],step,fail))ok=0;}
    }
    for(i=length<0?0:length;i<previous;++i)for(j=0;j<3;++j){tx_element_key(key,roots[3+j],i);if(!as_erase(c,key,step,fail))ok=0;}
    for(j=0;j<3;++j){as_length_key(key,roots[3+j]);if(length<0){if(!as_erase(c,key,step,fail))ok=0;}else if(!as_put(c,key,length*100000LL,step,fail))ok=0;}
    if(length<0){
        if(!as_erase(c,roots[0],step,fail))ok=0;
        if(!as_erase(c,roots[2],step,fail))ok=0;
        for(i=0;i<8;++i){as_owner_key(key,name,i);if(!as_erase(c,key,step,fail))ok=0;}
    }else if(!as_put(c,roots[2],length*100000LL,step,fail))ok=0;
    return ok;
}

static int as_matches(void* c,const char* name,char roots[6][40],long long parts[4096][3],int n,int gen,const unsigned int stamps[8])
{
    char key[48];long long raw;unsigned int current[8];int count,g,i,j,owned;
    if(n<0)return ag_inventory(c,roots,&owned)&&owned==0&&as_owner_absent(c,name);
    if(Array64Group_Read(c,name,-1,gen,&raw,&count,&g)!=2||count!=n||!ao_stamps(c,name,current))return 0;
    for(i=0;i<8;++i)if(current[i]!=stamps[i])return 0;
    for(i=0;i<n;++i)for(j=0;j<3;++j){tx_element_key(key,roots[3+j],i);if(na_lookup(c,key,&raw)!=1||raw!=parts[i][j])return 0;}
    return 1;
}

static int as_encode(long long raw,int wide,long long out[3])
{
    if(wide==0){if(raw<=-214748364800000LL||raw>=214748364800000LL)return 0;out[0]=raw;out[1]=out[2]=0;return 1;}
    if(wide!=1)return 0;
    {unsigned long long bits=(unsigned long long)raw;long long lo=(long long)(bits&4294967295ull),hi=(long long)(bits>>32);int flags=0;
    if(lo>=2147483648LL)lo-=4294967296LL;if(hi>=2147483648LL)hi-=4294967296LL;
    if(lo==-2147483648LL){lo=0;flags|=1;}if(hi==-2147483648LL){hi=0;flags|=2;}
    out[0]=lo*100000;out[1]=hi*100000;out[2]=(flags+1)*100000;}return 1;
}

int Array64_ShapeApply(void* c,const char* name,int op,int index,int expected_generation,long long raw,int wide,
    int size,const unsigned int* new_stamps,Array64ShapeWork* work,int fail_stage,int fail_compensation)
{
    char roots[6][40];long long encoded[3],value;int count,gen,owned,i,j,step=0,rollback=0,ok;
    if(!work||!ag_name(name,roots)||op<0||op>5||size<0||size>4096||fail_stage<0||fail_compensation<0||!as_encode(raw,wide,encoded))return -1;
    work->absent=op==0;
    if(op==0){
        if(expected_generation!=0||!new_stamps||!ag_inventory(c,roots,&owned)||owned||!as_owner_absent(c,name))return -2;
        for(i=0;i<8;++i){if(new_stamps[i]<1||new_stamps[i]>2147483647)return -1;work->stamps[i]=new_stamps[i];}
        work->old_length=-1;work->old_generation=0;work->new_length=size;
        for(i=0;i<size;++i)for(j=0;j<3;++j)work->next[i][j]=encoded[j];
    }else{
        if(Array64Group_Read(c,name,-1,expected_generation,&value,&count,&gen)!=2||gen>2147483644||!ao_stamps(c,name,work->stamps)||
            Array64_Capture(c,name,gen,42,&work->baseline)!=1)return -2;
        work->old_length=count;work->old_generation=gen;work->new_length=count;
        for(i=0;i<count;++i)for(j=0;j<3;++j)work->next[i][j]=work->baseline.parts[i][j];
        if(op==1||op==2){if(count==4096||(op==2&&(index<0||index>count)))return -1;index=op==1?count:index;work->new_length=count+1;
            for(i=count;i>index;--i)for(j=0;j<3;++j)work->next[i][j]=work->next[i-1][j];for(j=0;j<3;++j)work->next[index][j]=encoded[j];}
        else if(op==3){if(index<0||index>=count)return -1;work->new_length=count-1;for(i=index;i<count-1;++i)for(j=0;j<3;++j)work->next[i][j]=work->next[i+1][j];}
        else if(op==4)work->new_length=-1;
        else if(op==5){work->new_length=size;for(i=count;i<size;++i)for(j=0;j<3;++j)work->next[i][j]=encoded[j];}
    }
    gen=work->old_generation;
    if(!as_put(c,roots[1],(gen+1LL)*100000,&step,fail_stage))goto compensate;
    if(!as_install(c,name,roots,work->next,work->new_length,work->old_length<0?0:work->old_length,work->stamps,&step,fail_stage))goto compensate;
    ok=work->new_length<0?as_erase(c,roots[1],&step,fail_stage):as_put(c,roots[1],(gen+2LL)*100000,&step,fail_stage);
    if(ok&&as_matches(c,name,roots,work->next,work->new_length,gen+2,work->stamps))return 1;
compensate:
    if(!as_native_put(c,roots[1],(gen+1LL)*100000))return -4;
    ok=as_install(c,name,roots,work->baseline.parts,work->old_length,
        work->new_length>work->old_length?work->new_length:work->old_length,work->stamps,&rollback,fail_compensation);
    if(ok){
        ok=work->absent?as_erase(c,roots[1],&rollback,fail_compensation):as_put(c,roots[1],gen*100000LL,&rollback,fail_compensation);
        if(ok&&as_matches(c,name,roots,work->baseline.parts,work->old_length,gen,work->stamps))return 2;
    }
    if(!as_native_put(c,roots[0],200000)||!as_native_put(c,roots[2],(work->old_length<0?0:work->old_length)*100000LL)||
        !as_native_put(c,roots[1],(gen+1LL)*100000))return -4;
    return -3;
}
