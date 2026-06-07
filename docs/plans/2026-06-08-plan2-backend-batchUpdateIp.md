# Plan 2 — 后端 batchUpdateIp 精准重指接口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 fire-common 后端新增 `POST /api/app/appDomainManager/batchUpdateIp {ids[], ip}`，只重指传入的这批域名的 Cloudflare A 记录（原地改、不清空、零误伤），供流程3 调用。

**Architecture:** 照搬已有 `updateAppIp` 的内核但作用域改为「按 id 列表」——控制器收 `BatchUpdateIpReq{ids, ip}`，服务层循环调用已存在的 `updateIp(id, ip)`（改库 + `cloudflare.updateDnsRecord` 原地改 A 记录），单条失败不中断、收集汇总返回。

**Tech Stack:** Spring Boot 2.7 / MyBatis-Plus / Shiro(@RequiresPermissions) / Lombok / Knife4j。模块 `fire-common-app`（api 放实体&接口&DTO，biz 放实现&控制器）。

**测试说明（如实）：** `fire-common-app` 现无任何 `src/test`，无单元测试脚手架；为此接口单独引入 Spring 测试上下文不成比例且有风险。本计划采用 **编译通过 + 部署后真实接口冒烟** 验证，而非 JUnit。

**前置：** fire-common 仓库在分支 `new_master`（用户指定只用此分支）。路径前缀 `jeecg-boot/jeecg-boot-module/fire-common-app/`。

**参考规格：** [docs/specs/2026-06-08-app-domains-design.md](../specs/2026-06-08-app-domains-design.md) §7。

---

### Task 1: 新增 DTO `BatchUpdateIpReq`

**Files:**
- Create: `fire-common-app-api/src/main/java/org/jeecg/fire/common/modules/app/pojo/BatchUpdateIpReq.java`

- [ ] **Step 1: 写 DTO（仿同目录 BatchAddDomainReq 风格）**

写入 `BatchUpdateIpReq.java`：
```java
package org.jeecg.fire.common.modules.app.pojo;

import lombok.Data;

import java.util.List;

@Data
public class BatchUpdateIpReq {
    private List<String> ids;
    private String ip;
}
```

- [ ] **Step 2: 确认放在正确包路径**

Run:
```bash
cd "/Users/Funny/Library/CloudStorage/OneDrive-个人/MyProduct/FirePro/fire-common"
test -f jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-api/src/main/java/org/jeecg/fire/common/modules/app/pojo/BatchUpdateIpReq.java && echo "DTO OK"
```
Expected: `DTO OK`。

---

### Task 2: 服务接口加方法声明

**Files:**
- Modify: `fire-common-app-api/.../service/IAppDomainManagerService.java`

- [ ] **Step 1: 在接口里 `void ipAppSync();` 之后新增声明**

在 `IAppDomainManagerService` 中、`void ipAppSync();` 行之后加：
```java

    /** 按 id 列表批量原地重指 CF A 记录到指定 ip。单条失败不中断,返回汇总文案。 */
    String batchUpdateIp(java.util.List<String> ids, String ip);
```

- [ ] **Step 2: 确认声明存在**

Run:
```bash
cd "/Users/Funny/Library/CloudStorage/OneDrive-个人/MyProduct/FirePro/fire-common"
grep -n "batchUpdateIp" jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-api/src/main/java/org/jeecg/fire/common/modules/app/service/IAppDomainManagerService.java
```
Expected: 显示新增的 `String batchUpdateIp(...)` 行。

---

### Task 3: 服务实现 `batchUpdateIp`

**Files:**
- Modify: `fire-common-app-biz/.../service/impl/AppDomainManagerServiceImpl.java`

- [ ] **Step 1: 实现方法（复用已存在的 `updateIp`，单条 try/catch）**

在 `AppDomainManagerServiceImpl` 类内（如紧接现有 `ipAppSync()` 实现之后）新增：
```java
    @Override
    public String batchUpdateIp(java.util.List<String> ids, String ip) {
        int success = 0;
        java.util.List<String> failed = new java.util.ArrayList<>();
        for (String id : ids) {
            try {
                // updateIp 内部:改库 + cloudflare.updateDnsRecord 原地改 A 记录;
                // 其对 Authentication error / Record does not exist 会自行标 status=-1,
                // 其它错误会抛出,这里捕获以保证单条失败不中断整批。
                updateIp(id, ip);
                success++;
            } catch (Exception e) {
                failed.add(id);
                log.error("batchUpdateIp 失败 id={} ip={} : {}", id, ip, e.getMessage());
            }
        }
        String msg = "成功" + success + "个,失败" + failed.size() + "个"
                + (failed.isEmpty() ? "" : ",失败id:" + String.join(",", failed));
        log.info("batchUpdateIp 完成:{}", msg);
        return msg;
    }
```

- [ ] **Step 2: 确认实现存在且类已实现接口新方法**

Run:
```bash
cd "/Users/Funny/Library/CloudStorage/OneDrive-个人/MyProduct/FirePro/fire-common"
grep -n "public String batchUpdateIp" jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-biz/src/main/java/org/jeecg/fire/common/modules/app/service/impl/AppDomainManagerServiceImpl.java
```
Expected: 显示该实现方法签名行。

---

### Task 4: 控制器加 `/batchUpdateIp` 端点

**Files:**
- Modify: `fire-common-app-biz/.../controller/AppDomainManagerController.java`

- [ ] **Step 1: 加 import**

在 import 区，`import org.jeecg.fire.common.modules.app.pojo.BatchAddDomainReq;` 之后加：
```java
import org.jeecg.fire.common.modules.app.pojo.BatchUpdateIpReq;
```

- [ ] **Step 2: 在 `batchAddDomains` 方法之后新增端点**

在 `AppDomainManagerController` 内（紧接现有 `batchAddDomains(...)` 方法之后）加：
```java
	@AutoLog(value = "应用域名管理-按ID批量重指IP")
	@Operation(summary="按ID批量重指IP(原地改CF A记录,仅传入的这批)")
	@RequiresPermissions("app:app_domain_manager:edit")
	@PostMapping(value = "/batchUpdateIp")
	public Result<String> batchUpdateIp(@RequestBody BatchUpdateIpReq req) {
		if (req.getIds() == null || req.getIds().isEmpty()) {
			return Result.error("ids 不能为空");
		}
		if (req.getIp() == null || req.getIp().isBlank()) {
			return Result.error("ip 不能为空");
		}
		String msg = appDomainManagerService.batchUpdateIp(req.getIds(), req.getIp());
		return Result.OK(msg);
	}
```

- [ ] **Step 3: 确认端点存在**

Run:
```bash
cd "/Users/Funny/Library/CloudStorage/OneDrive-个人/MyProduct/FirePro/fire-common"
grep -n "batchUpdateIp\|BatchUpdateIpReq" jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-biz/src/main/java/org/jeecg/fire/common/modules/app/controller/AppDomainManagerController.java
```
Expected: 显示 import 与 `@PostMapping("/batchUpdateIp")` 端点。

---

### Task 5: 编译验证

**Files:** 无（仅构建）

- [ ] **Step 1: 编译 fire-common-app（含其依赖模块）**

Run:
```bash
cd "/Users/Funny/Library/CloudStorage/OneDrive-个人/MyProduct/FirePro/fire-common/jeecg-boot"
mvn -q -pl jeecg-boot-module/fire-common-app/fire-common-app-biz -am compile 2>&1 | tail -20
```
Expected: `BUILD SUCCESS`（无编译错误）。若因环境缺依赖，退化为整体 `mvn -q -am -pl jeecg-boot-module/fire-common-app/fire-common-app-biz install -DskipTests`。

---

### Task 6: 提交（new_master 分支）

- [ ] **Step 1: 提交三处改动**

Run:
```bash
cd "/Users/Funny/Library/CloudStorage/OneDrive-个人/MyProduct/FirePro/fire-common"
git add jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-api/src/main/java/org/jeecg/fire/common/modules/app/pojo/BatchUpdateIpReq.java \
        jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-api/src/main/java/org/jeecg/fire/common/modules/app/service/IAppDomainManagerService.java \
        jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-biz/src/main/java/org/jeecg/fire/common/modules/app/service/impl/AppDomainManagerServiceImpl.java \
        jeecg-boot/jeecg-boot-module/fire-common-app/fire-common-app-biz/src/main/java/org/jeecg/fire/common/modules/app/controller/AppDomainManagerController.java
git commit -m "$(cat <<'EOF'
feat(app): 域名管理新增按ID批量重指IP接口 batchUpdateIp

新增 BatchUpdateIpReq DTO 与 /batchUpdateIp 端点,服务层循环复用
updateIp 原地改 CF A 记录,仅作用于传入的 id 列表,单条失败不中断。
供域名分配流程(流程3)精准重指,避免 updateAppIp 全项目重指的误伤。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1
```
Expected: 提交成功。

---

### Task 7: 部署 + 真实接口冒烟（用户动作）

> 后端需用户构建并部署到线上 `firepikatacommon.huozhongtech.org` 后才生效。

- [ ] **Step 1: 构建并部署**（用户按既有发布流程；如 `mvn clean package` + 重启/docker）。

- [ ] **Step 2: 真实冒烟（拿一个已知空域名 id 测）**

取一个 status=1 的空域名（其 zoneId=id，当前 ip=128.241.233.59），用有 `app:app_domain_manager:edit` 权限的 token：
```bash
TOKEN="<X-Access-Token>"
curl -s -X POST "https://firepikatacommon.huozhongtech.org/api/app/appDomainManager/batchUpdateIp" \
  -H "X-Access-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"ids":["<zoneId>"],"ip":"<项目appIp>"}'
```
Expected: 返回 `{"success":true,...,"result":"成功1个,失败0个"}`。

- [ ] **Step 3: 核对生效**

- 后台「应用域名管理」该域名 ip 列变为 `<项目appIp>`；
- Cloudflare 上该域名 A 记录指向 `<项目appIp>`（原地改，未清空其它 DNS）；
- 用错误 id 再测一次，返回 `成功0个,失败1个,失败id:...`，证明单条失败不影响其它、不抛 500。

---

## 自检（Self-Review）

- **Spec 覆盖**：对应 spec §7——DTO(Task1)、接口声明(Task2)、实现循环 updateIp+单条容错(Task3)、控制器端点+权限+校验(Task4)、编译(Task5)、提交(Task6)、部署+冒烟(Task7)。✅
- **占位符**：无 TBD；每步含确切代码/命令与期望输出。✅
- **类型一致**：DTO 字段 `ids`/`ip`；接口与实现签名均 `String batchUpdateIp(List<String> ids, String ip)`；控制器 `req.getIds()/req.getIp()` 与 DTO 一致；复用的 `updateIp(String id, String ip)` 与现有签名一致。✅
- **风险**：`updateIp` 对 auth/record-not-exist 会标 status=-1（既有行为）；本接口只对**传入的 id**生效，不波及项目其它域名（这正是相对 updateAppIp 的改进）。✅
