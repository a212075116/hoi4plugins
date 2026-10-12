import json,pathlib,re,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
package=pathlib.Path(sys.argv[1]).resolve()
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 docs={n:z.read(n).decode('utf-8-sig') for n in z.namelist() if n.endswith('.md') and n.startswith(('ai_docs/','test/docs/'))}
todo=docs.get('test/docs/用户尚未测试的待办事项.md','');state=docs.get('ai_docs/09_脚本数值系统/当前状态与复现.md','');design=docs.get('ai_docs/05_工具链/外部调试控制台可行性与接口方案.md','')
rows=[{'key':'named_user_todo_exists','ok':todo.startswith('# 用户尚未测试的待办事项')},
 {'key':'user_visual_and_interaction_tasks','ok':all(x in todo for x in ['U01','U02','真实游戏画面'])},
 {'key':'automatable_or_power_loss_not_checklist','ok':not re.search(r'^- \[ \].*(资源|掉电|哈希|原生夹具)',todo,re.M)},
 {'key':'current_growth_accepted_and_2GB_severity','ok':all(x in state for x in ['用户接受当前增量','2GB','不是总占用上限'])},
 {'key':'power_loss_not_required','ok':'不作为必须目标' in state},
 {'key':'console_state_declared','ok':'未编写或部署' in design or ('已实现' in design and 'U04' in todo)},
 {'key':'bidirectional_plan_and_safe_dispatch','ok':all(x in design for x in ['增量读取','有界请求队列','不能从任意管道线程','ACL'])}]
result={'package':str(package),'checks':len(rows),'passed':sum(r['ok'] for r in rows),'rows':rows};result['exit']=int(result['checks']!=result['passed']);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(result['exit'])
