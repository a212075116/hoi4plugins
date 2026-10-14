# Array64记录与所有权键模块

2026-10-14，第十五批。统一真实重复机制，不改持久化协议或恢复流程。

## 私有接口

`src/plugin/SDK_RVA/variable64/array64_wire.h`集中原有 `ad_get/ad_put/ad_hash`和共用的 `ad_i64/ad_i32`。
前者负责小端读写及原FNV-1a字节校验；后者保留原来的有符号位模式转换，避免把越界unsigned直接转signed。
三个signed64内联表达式和原journal signed32函数由共同实现取代。

`array64_owner_key.h`持有原 `as_owner_key`，所有权stamp读取和形状事务共用它。
原来两处独立构造的 `__v64o_NAME_b0..b3/i0..i3`现在只有一份生成规则。
调用前的名称验证、stamp读取顺序和失败返回没有改变。

两个头文件都是私有纯计算，没有Windows、存储对象、文件或内存分配依赖，也不增加公有API。
wire调用者仍须预先验证缓冲和宽度：读写宽度0..8、signed读取4/8字节；函数不新加截断或错误码。
owner调用者仍提供合法、不变的1..20字节名称、索引0..7以及足够输出空间。

## 不合并的机制

内存snapshot的 `ar_hash`包含owner、当前container身份及成员顺序，不是wire记录校验，保留独立语义。
scalar64存储、原版哈希表索引、远程命令目录的进程读取也不因外观相似就套用wire模块。
日志文件与journal的flush、replace、重读校验不是同一种写入策略，本批不改其恢复顺序。

## 原编译归属

生产只有 `array64_api.c`是独立编译单元；其private实现链保持原样：

```text
array64_api.c
  -> array64_shape_journal.c
    -> array64_shape_transaction.c
      -> array64_ownership_gate.c (+ owner_key.h)
        -> array64_durable_snapshot.c (+ wire.h)
          -> array64_recovery.c
            -> array64_existing_transaction.c
              -> array64_group_readonly.c
                -> native_array_readonly.c
```

不能把这些被包含的 `.c`额外作为ClCompile加入工程，否则会重复定义。
本批只补齐两个头文件的工程列表，未搬动API实现或新增编译单元。

## 保持的协议和证据

magic、版本、字段偏移、小端顺序、scope/lineage/owner/nonce/generation规则及错误码不变。
名称、snapshot/quarantine状态、事务写入、隔离、重试和恢复顺序不变。
8000组wire oracle与4000组owner键，168000项检查通过；durable411、ownership211、shape287、journal244三态输出一致。
三个实际导出记录的完整字节三态SHA一致，含4096元素的大型baseline和owned记录。
Debug/Release、其他数值/注册器/日志回归、源码/DLL副本及完整包回滚通过。
新DLL未部署，未运行游戏；模型内存与写入适配器不是实机持久化新验收。
执行说明见[记录/所有权键回归](../../test/docs/array64_helpers.md)。
