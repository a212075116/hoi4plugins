# 外部控制台日志颜色

2026-10-13。`Print`按每个物理文本行的方括号级别标签设置整行前景色，标签不区分ASCII大小写。

| 标签 | 前景色 |
|---|---|
| `[error]`、`[fatal]` | 亮红 |
| `[warning]`、`[warn]`、`[waring]` | 亮黄；兼容用户输入的拼写 |
| `[success]`、`[ok]`、`[pass]` | 亮绿 |
| `[info]`、`[notice]` | 亮青 |
| `[debug]`、`[trace]` | 深灰 |
| 无上述标签 | 原终端默认颜色 |

同一行多标签时按错误、警告、成功、信息、调试的顺序优先匹配。
来源前缀也属于标签：已有`[ERROR]`来源的error.log输出整行红色；`[GAME]`和`[PLUGIN]`自身不代表严重级别。
颜色覆盖来源前缀及整行内容，而不只是括号里的标签；多行文本各自分类。
只改低4位前景色，保留背景和原有其他属性；输出结束恢复原颜色，再绘制输入提示。
不往日志文件或重定向stdout加入ANSI颜色码，不修改权限、游戏状态或滚轮输入模式。
终端调色板决定具体色调，真实字体/DPI/主题的舒适度见[U04](用户尚未测试的待办事项.md)。

## 回归

```powershell
python test/modules/console/run_color_regression.py MODIFIED
```

包含真实`Print`源码：API模型19项与真实ConPTY私有屏幕缓冲区19项。
原生检查读取实际字符单元及前景/背景属性，中文宽字符按leading/trailing单元处理；不是GUI截图验收。

| 状态 | 模型 | 原生属性 | 退出码 |
|---|---|---|---|
| BASELINE | 6/19 | 6/19 | 1 |
| MODIFIED | 19/19 | 19/19 | 0 |
| ROLLBACK | 6/19 | 6/19 | 1 |

覆盖大小写、waring/warning/warn、整行、级别优先级、中文、多行独立着色、背景与提示恢复、API失败退化及重定向保持纯文本。
压力检查为10000次模型输出与100次真实缓冲区输出；不冒充10000次原生输出或重跑此前45分钟抗压。
证据位于`test/reports/20261012_variable64_transaction/console_colors/`；保留首次字符单元探针误判及更正记录。
相关：[控制台入口](external_console.md)、[权限策略](console_permission.md)。
