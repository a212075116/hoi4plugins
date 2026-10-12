#include "array64_recovery.c"

static unsigned long long ad_get(const unsigned char* p, int n)
{
    unsigned long long v = 0;
    int i;
    for (i = 0; i < n; ++i) v |= (unsigned long long)p[i] << (8*i);
    return v;
}

static void ad_put(unsigned char* p, unsigned long long v, int n)
{
    int i;
    for (i = 0; i < n; ++i) p[i] = (unsigned char)(v >> (8*i));
}

static unsigned long long ad_hash(const unsigned char* p, unsigned int n)
{
    unsigned long long h = 14695981039346656037ull;
    unsigned int i;
    for (i = 0; i < n; ++i) h = (h ^ p[i]) * 1099511628211ull;
    return h;
}

static int ad_scope(const char* s)
{
    int n = 0, i;
    if (!s) return 0;
    while (s[n]) { if (n >= 80) return 0; ++n; }
    if (n == 6 && s[0]=='g' && s[1]=='l' && s[2]=='o' && s[3]=='b' && s[4]=='a' && s[5]=='l') return n;
    if (n == 11 && s[0]=='c' && s[1]=='o' && s[2]=='u' && s[3]=='n' && s[4]=='t' && s[5]=='r' && s[6]=='y' && s[7]==':') {
        for (i=8;i<11;++i) if (s[i]<'A' || s[i]>'Z') return 0;
        return n;
    }
    if (n > 6 && s[0]=='s' && s[1]=='t' && s[2]=='a' && s[3]=='t' && s[4]=='e' && s[5]==':' && s[6]>='1' && s[6]<='9') {
        unsigned long long id=0;
        for (i=6;i<n;++i) { if (s[i]<'0'||s[i]>'9') return 0; id=id*10+(s[i]-'0'); if(id>2147483647) return 0; }
        return n;
    }
    if (n>10 && s[0]=='c'&&s[1]=='h'&&s[2]=='a'&&s[3]=='r'&&s[4]=='a'&&s[5]=='c'&&s[6]=='t'&&s[7]=='e'&&s[8]=='r'&&s[9]==':') {
        for(i=10;i<n;++i) if (!((s[i]>='A'&&s[i]<='Z')||(s[i]>='a'&&s[i]<='z')||(s[i]>='0'&&s[i]<='9')||s[i]=='_')) return 0;
        return n;
    }
    return 0;
}

int Array64_ExportBaseline(const Array64Snapshot* snapshot, const char* scope, unsigned long long lineage,
    unsigned char* output, unsigned int capacity, unsigned int* written)
{
    char roots[6][40];
    unsigned int n=0, total, pos, i, j;
    int scope_length=ad_scope(scope);
    if (!snapshot || !output || !written || !lineage || !scope_length || snapshot->magic!=0x3250414e53343641ull ||
        snapshot->consumed || snapshot->length<0 || snapshot->length>4096 || snapshot->generation<0 ||
        snapshot->generation>2147483644 || snapshot->generation%2 || snapshot->name[20]!=0 ||
        !ag_name(snapshot->name,roots) || snapshot->checksum!=ar_hash(snapshot)) return -1;
    while(snapshot->name[n])++n;
    for(i=0;i<(unsigned int)snapshot->length;++i)if(!ar_valid_parts(snapshot->parts[i]))return -1;
    total=48+(unsigned int)scope_length+n+24*(unsigned int)snapshot->length;
    if(capacity<total)return -2;
    ad_put(output,0x3245534142343641ull,8);ad_put(output+8,1,4);ad_put(output+12,2,4);
    ad_put(output+16,(unsigned int)snapshot->length,4);ad_put(output+20,(unsigned int)snapshot->generation,4);
    ad_put(output+24,lineage,8);ad_put(output+32,(unsigned int)scope_length,4);ad_put(output+36,n,4);
    pos=40;
    for(i=0;i<(unsigned int)scope_length;++i)output[pos++]=(unsigned char)scope[i];
    for(i=0;i<n;++i)output[pos++]=(unsigned char)snapshot->name[i];
    for(i=0;i<(unsigned int)snapshot->length;++i)for(j=0;j<3;++j){ad_put(output+pos,(unsigned long long)snapshot->parts[i][j],8);pos+=8;}
    ad_put(output+pos,ad_hash(output,pos),8);*written=total;
    return 1;
}

int Array64_ImportBaseline(void* current_container, const char* expected_name, const char* resolved_scope,
    unsigned long long current_lineage, unsigned long long fresh_owner, const unsigned char* record,
    unsigned int bytes, Array64Snapshot* snapshot)
{
    char roots[6][40], scope[81], name[21];
    unsigned int n, scope_length, length, gen, total, pos, i, j;
    int count, odd;
    if(!snapshot)return -1;
    snapshot->magic=0;
    if(!record || bytes<48 || !current_container || !fresh_owner || !current_lineage || !ag_name(expected_name,roots) ||
        !ad_scope(resolved_scope))return -1;
    if(ad_get(record,8)!=0x3245534142343641ull || ad_get(record+8,4)!=1 || ad_get(record+12,4)!=2)return -2;
    length=(unsigned int)ad_get(record+16,4);gen=(unsigned int)ad_get(record+20,4);
    scope_length=(unsigned int)ad_get(record+32,4);n=(unsigned int)ad_get(record+36,4);
    if(length>4096 || gen>2147483644 || gen%2 || scope_length<1 || scope_length>80 || n<1 || n>20)return -3;
    total=48+scope_length+n+24*length;
    if(bytes!=total || ad_get(record+total-8,8)!=ad_hash(record,total-8))return -3;
    if(ad_get(record+24,8)!=current_lineage)return -4;
    pos=40;
    for(i=0;i<scope_length;++i)scope[i]=(char)record[pos++];scope[scope_length]=0;
    for(i=0;i<n;++i){name[i]=(char)record[pos++];if(!name[i])return -3;}name[n]=0;
    if(ad_scope(scope)!=(int)scope_length || !ag_name(name,roots))return -3;
    for(i=0;i<=scope_length;++i){if(scope[i]!=resolved_scope[i])return -4;if(!scope[i])break;}
    for(i=0;i<=n;++i){if(name[i]!=expected_name[i])return -4;if(!name[i])break;}
    if(Array64_InspectQuarantine(current_container,expected_name,&count,&odd)!=1 || count!=(int)length || odd!=(int)gen+1)return -5;
    snapshot->owner=fresh_owner;snapshot->container=current_container;snapshot->length=(int)length;
    snapshot->generation=(int)gen;snapshot->consumed=0;
    for(i=0;i<21;++i)snapshot->name[i]=i<n?name[i]:0;
    for(i=0;i<length;++i)for(j=0;j<3;++j){
        unsigned long long bits=ad_get(record+pos,8);pos+=8;
        snapshot->parts[i][j]=bits<=9223372036854775807ull?(long long)bits:-1-(long long)(~bits);
    }
    for(i=0;i<length;++i)if(!ar_valid_parts(snapshot->parts[i]))return -3;
    snapshot->checksum=ar_hash(snapshot);snapshot->magic=0x3250414e53343641ull;
    return 1;
}
