# deploy-project skill — 设计 (2026-06-08)

## 目标
在 fire_h5(前台) / fire_admin(后台) 仓库里，用户说**"提交并推送"**（或"发布"/"部署项目"），自动跑完整发布流水线：
git push → Jenkins 构建 → 宝塔对应面板执行更新命令。把本人手工跑过的前台流程固化，并补上后台。

## 形态与位置（方案 B）
- **位置**：`fire-domain-ops` 插件新增
  - `skills/deploy-project/SKILL.md` —— 编排 + 判断（前/后台识别、web1 检测、确认、报告）
  - `scripts/jenkins.py` —— Jenkins 触发/轮询/读密钥（确定性、易错部分写死在脚本）
- **复用**：面板查找 + 执行复用同插件的 `scripts/bt.py`（`find-site` + `exec`，exec 已是 crontab 修复版）
- **密钥**：`~/.fire/jenkins.json`（`{url,user,token}`，gitignore，**绝不进插件仓库**），`jenkins.py` 读它。首次用需创建，README/setup 说明。

## 触发与识别
- **触发**：在 fire_h5 或 fire_admin 仓库里，用户说"提交并推送 / 发布 / 部署"。非这两个仓库不适用。
- **前台 vs 后台**：当前 git 仓库（目录名/remote）→ `fire_h5`=前台、`fire_admin`=后台。
- **项目编号**（前台）：从分支名取，如 `fireXXX-F076` → `f076`。后台恒为 `fadmin`。

## 流程
1. 暂存 + 提交（给用户看 diff 摘要 + 提交信息）+ push 到 Gitea。
2. **前台**：检测本次提交是否改了 `web1-static/`（`git diff` 范围内）→ 决定是否"先删 web1"。后台无此步。
3. `jenkins.py build <job> --wait`：
   - 前台 job = `fire_h5_f<NN>`；后台 job = `fire_admin_web`
   - 报 SUCCESS/FAIL，**失败则中止，不部署**。
4. `bt.py find-site <站点>` → 主网关 + 专用面板（按物理机去重）：
   - 前台站点 = `f<NN>_app`；后台站点 = `fadmin`
5. **生产确认一次**（列出目标面板 + 将执行的命令）→ `bt.py exec` 逐面板部署：
   - 前台：`cd /root && sh deploy_h5.sh f<NN>`
     - 若动了 web1：`rm -rf /www/wwwroot/f<NN>_app/web1 && cd /root && sh deploy_h5.sh f<NN>`
   - 后台：`cd /root && sh deploy.sh fadmin`
6. 验证（部署后 grep 关键改动 / 检查站点文件 mtime）+ 汇报每台面板结果。

## jenkins.py 接口（初定）
读 `~/.fire/jenkins.json`。子命令：
- `build <job> [--wait] [--timeout N]` —— 触发构建，`--wait` 轮询到结束并返回 SUCCESS/FAILURE + 构建号
- `status <job>` —— 最近一次构建 building/result
- `console <job> [N]` —— 拉 console（排障）

## 安全
- **push** 由"提交并推送"这句话授权（即触发即提交推送）。
- **生产面板部署前确认一次**（列面板 + 命令）。← 可改成全自动（见待定项）。
- Jenkins 失败一律中止部署。

## 待定项（默认值，用户 review 时可改）
- **生产确认闸**：默认**保留**（部署前确认一次）。可改全自动。
- **skill 名**：默认 `deploy-project`。

## 非目标 (YAGNI)
- 不做回滚、不做多项目批量发布、不做 web1 单独发布命令（web1 跟前台一起走"删了再部署"）。
- 不处理 `fire_admin_NNN` 这类按编号的后台 job（确认不存在）。
