# OpenClaw Queue Watcher V3 To-Do

## Current Implementation Summary

Queue Watcher V3 is now the preferred trigger path for async workflow
execution. The watcher watches only the pending queue and wakes
`queue-dispatcher-agent` when work appears. Cron remains a fallback trigger for
environments where the watcher is unavailable or temporarily stopped.

The dispatcher agent should call `crypto_helper_queue_dispatch_until_empty`
once per wakeup and should not manually loop through claim / worker / mark /
finalize tools during normal operation. Worker results are converted into
manager handoff payloads, then flow back to `manager-agent`. `manager-agent`
remains the final owner of user-facing output.

---

本文档用于指导 Codex 在 V2 `dispatch-until-empty` 的基础上，继续增加一个后台 watcher：

```text
当 pending 队列为空时安静等待；
一旦 pending 队列非空，立即唤醒 queue-dispatcher-agent；
queue-dispatcher-agent 再调用 dispatch-until-empty 批量处理队列；
worker 完成后结果回流给 manager-agent；
manager-agent 负责最终用户输出。
```

本文件只提供设计和逐步 prompt，不直接实现代码。

---

## 0. V3 目标架构

### 推荐链路

```text
manager-agent
  -> crypto_helper_manager_handle_request
  -> direct_result 或 enqueue DelegationTask
  -> pending queue
  -> queue-watcher 后台程序检测 pending 非空
  -> queue-watcher 唤醒 queue-dispatcher-agent
  -> queue-dispatcher-agent 调用 crypto_helper_queue_dispatch_until_empty
  -> Python orchestrator 批量 claim / worker / mark / finalize / manager handoff
  -> manager-agent 接收 worker result handoff
  -> manager-agent 输出最终用户回复
```

### 职责划分

`queue-watcher`：

- 只监听队列状态
- 只负责唤醒 `queue-dispatcher-agent`
- 不 claim task
- 不调用 worker
- 不 finalize
- 不给用户输出

`queue-dispatcher-agent`：

- 只作为后台调度 agent
- 每次被唤醒后调用 `crypto_helper_queue_dispatch_until_empty`
- 不直接处理公开聊天
- 不直接输出给用户

Python orchestrator：

- 真正执行循环消费
- 保证 `max_tasks` / `max_seconds`
- 保证单个 task 失败不会中断整轮
- 负责 worker adapter / queue mark / manager handoff

`manager-agent`：

- 唯一用户-facing 输出归口
- 接收 worker result handoff
- 最终回复用户

---

## 1. V3 与 V2 的关系

V3 不替代 V2，而是建立在 V2 上。

必须先完成 V2：

- `DispatchLoopResult`
- `ManagerHandoffResult`
- `process_queued_workflows_until_empty`
- `crypto-helper queue dispatch-until-empty`
- `crypto_helper_queue_dispatch_until_empty`
- `crypto-helper manager receive-worker-result`
- `crypto_helper_manager_receive_worker_result`
- `queue-dispatcher-agent` 使用 dispatch-until-empty

V3 新增：

- `queue watch` CLI
- watcher lock
- watcher cooldown
- OpenClaw agent wake-up adapter
- optional systemd user service
- cron fallback 保留

---

## 2. 为什么 watcher 比纯 cron 更合适

纯 cron：

```text
每 1 分钟唤醒一次 queue-dispatcher-agent
```

问题：

- 最坏延迟接近 60 秒
- 队列为空时仍会唤醒 agent
- 不是真正 event-driven

watcher：

```text
pending 非空 -> 立即唤醒 queue-dispatcher-agent
```

优势：

- 延迟更低
- 没任务时更安静
- 更符合异步队列语义
- 面试中更容易解释为后台调度系统

保留 cron fallback 的原因：

- watcher 进程可能被停止
- OpenClaw gateway 可能暂时不可用
- 文件监听可能丢事件
- cron 可以作为兜底补偿调度

---

## 3. 关键设计决策

### 3.1 watcher 不直接处理业务

禁止：

```text
queue-watcher -> claim task -> worker -> finalize
```

必须：

```text
queue-watcher -> wake queue-dispatcher-agent
```

原因：

- watcher 是 runtime trigger，不是业务调度器
- worker 选择和 manager handoff 仍由 Python orchestrator / dispatcher flow 统一处理
- 避免 watcher 和 dispatcher 双重消费队列

### 3.2 dispatcher 一次处理到队列为空

watcher 只负责发现“非空”这个事件。

真正清空队列的是：

```text
crypto_helper_queue_dispatch_until_empty
```

它必须有上限：

```text
max_tasks default: 10
max_seconds default: 120
```

### 3.3 watcher 必须有 lock

避免多个 watcher 同时触发：

```text
watcher A 发现 pending 非空
watcher B 同时发现 pending 非空
两个 watcher 同时唤醒 dispatcher
```

建议 runtime lock：

```text
crypto_helper_data/queues/.watcher.lock
```

lock 内容建议：

```json
{
  "pid": 12345,
  "started_at": "...",
  "heartbeat_at": "...",
  "ttl_seconds": 60
}
```

### 3.4 watcher 必须有 cooldown

避免持续重复唤醒：

```text
pending 非空 -> wake dispatcher
dispatcher 还没处理完 -> watcher 又 wake
```

建议：

```text
cooldown default: 5s
```

或者：

```text
only wake when pending_count transitions from 0 to >0
```

第一版推荐 polling + cooldown，简单可靠。

---

## 4. Step 1: 审计 V2 前置条件

### 目标

确认当前仓库是否已经完成 V2 所需能力。

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后只做审计，不要修改代码。

目标：
确认当前仓库是否已具备 Queue Watcher V3 的前置条件。

重点检查：
1. 是否已有 process_queued_workflows_until_empty。
2. 是否已有 crypto-helper queue dispatch-until-empty --json。
3. 是否已有 crypto_helper_queue_dispatch_until_empty plugin tool。
4. 是否已有 manager receive-worker-result CLI / plugin tool。
5. queue-dispatcher-agent 是否已改成优先调用 dispatch-until-empty。
6. worker 完成后是否会生成 manager-agent handoff。

输出：
1. 已完成项
2. 缺失项
3. V3 开始前必须补齐的最小清单

不要改任何文件。
```

---

## 5. Step 2: 增加队列状态 helper

### 目标

watcher 需要低成本判断 pending queue 是否为空。

### 建议新增

```text
src/crypto_helper/agent_runtime/queue.py
```

新增函数：

```text
get_queue_counts()
has_pending_tasks()
```

返回结构建议：

```json
{
  "pending": 2,
  "processing": 0,
  "done": 10,
  "failed": 1
}
```

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后为 agent_runtime queue 增加轻量队列状态 helper。

要求：
1. 在 src/crypto_helper/agent_runtime/queue.py 中新增：
   - get_queue_counts()
   - has_pending_tasks()
2. 不改变现有 enqueue / claim / done / failed 行为。
3. 增加单元测试。

测试要求：
- 空队列 pending=0
- enqueue 后 pending 增加
- claim 后 pending 减少、processing 增加
- done / failed 后对应计数正确

完成后运行：
- uv run ruff format .
- uv run ruff check .
- uv run mypy src tests
- uv run pytest
```

---

## 6. Step 3: 增加 watcher lock

### 目标

保证同一时间只有一个 watcher 实例负责唤醒 dispatcher。

### 建议新增文件

```text
src/crypto_helper/agent_runtime/watcher_lock.py
tests/test_watcher_lock.py
```

### 建议接口

```text
acquire_watcher_lock(ttl_seconds=60) -> bool
refresh_watcher_lock()
release_watcher_lock()
get_watcher_lock_status()
```

### 设计要求

- lock 文件放在 runtime data：

```text
crypto_helper_data/queues/.watcher.lock
```

- 如果 lock 过期，可以被新 watcher 接管。
- release 只能删除当前进程持有的 lock。
- 测试里不要依赖真实 sleep，优先 monkeypatch time。

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后为 queue watcher 增加本地 lock。

要求：
1. 新增：
   - src/crypto_helper/agent_runtime/watcher_lock.py
   - tests/test_watcher_lock.py
2. lock 路径：
   - crypto_helper_data/queues/.watcher.lock
3. 实现：
   - acquire_watcher_lock(ttl_seconds=60)
   - refresh_watcher_lock()
   - release_watcher_lock()
   - get_watcher_lock_status()
4. lock 内容包含：
   - pid
   - started_at
   - heartbeat_at
   - ttl_seconds
5. 过期 lock 可以被接管。
6. 不引入外部依赖。

测试要求：
- 第一次 acquire 成功
- 第二次 acquire 在未过期时失败
- 过期后可重新 acquire
- release 后可再次 acquire

完成后运行：
- uv run ruff format .
- uv run ruff check .
- uv run mypy src tests
- uv run pytest
```

---

## 7. Step 4: 增加 OpenClaw dispatcher wake adapter

### 目标

watcher 发现 pending 非空时，需要唤醒 `queue-dispatcher-agent`。

### 推荐第一版实现

使用 OpenClaw CLI：

```bash
openclaw agent \
  --agent queue-dispatcher-agent \
  --message "Process the crypto_helper async delegation queue..."
```

如果当前 OpenClaw CLI 参数不是 `--agent`，Codex 必须先运行：

```bash
openclaw agent --help
```

然后适配本机版本。

### 建议新增文件

```text
src/crypto_helper/agent_runtime/openclaw_wakeup.py
tests/test_openclaw_wakeup.py
```

### 设计要求

- 只负责唤醒 agent。
- 不处理 task。
- 不解析 worker result。
- subprocess 调用必须可测试，测试中 monkeypatch command runner。
- 失败时返回结构化 warning，不让 watcher 崩溃。

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后新增 OpenClaw queue-dispatcher-agent wake adapter。

要求：
1. 新增：
   - src/crypto_helper/agent_runtime/openclaw_wakeup.py
   - tests/test_openclaw_wakeup.py
2. 实现：
   - wake_queue_dispatcher_agent(message: str | None = None) -> dict
3. 默认唤醒目标：
   - queue-dispatcher-agent
4. 默认 message：
   - Process the crypto_helper async delegation queue. Call crypto_helper_queue_dispatch_until_empty with max_tasks=10 and max_seconds=120. Return DispatchLoopResult only.
5. 使用 OpenClaw CLI 或本机支持的等价方式唤醒 agent。
6. 不直接调用 worker tools。
7. 不实现 Discord / Telegram runtime。
8. 测试中不要真的调用 OpenClaw，使用 monkeypatch。

执行前先检查：
- openclaw agent --help

完成后运行：
- uv run ruff format .
- uv run ruff check .
- uv run mypy src tests
- uv run pytest
```

---

## 8. Step 5: 实现 queue watch CLI

### 目标

新增一个可长期运行的 watcher 命令。

### 新增命令

```bash
uv run crypto-helper queue watch --json
```

建议参数：

```text
--poll-interval 2
--cooldown 5
--lock-ttl 60
--once
--max-wakeups
```

### 行为

```text
acquire lock
loop:
  refresh lock
  check pending count
  if pending > 0 and cooldown passed:
      wake queue-dispatcher-agent
      record wakeup
  if --once:
      exit after one check or one wakeup
  sleep poll_interval
release lock on exit
```

### 输出

`--once --json` 应返回：

```json
{
  "ok": true,
  "pending": 1,
  "woke_dispatcher": true,
  "cooldown_active": false,
  "lock_acquired": true
}
```

长期运行时可以输出 JSONL 或周期性 status。第一版只要求 `--once --json` 测试稳定。

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后新增 queue watcher CLI。

新增命令：
- uv run crypto-helper queue watch --json

参数：
- --poll-interval，默认 2
- --cooldown，默认 5
- --lock-ttl，默认 60
- --once
- --max-wakeups，可选

要求：
1. watcher 只检查 pending queue 是否非空。
2. pending 非空时调用 wake_queue_dispatcher_agent。
3. watcher 不 claim task。
4. watcher 不调用 worker。
5. watcher 不 finalize。
6. watcher 必须使用 watcher lock，防止多实例。
7. watcher 必须有 cooldown，防止重复唤醒。
8. --once 模式必须适合测试。

测试要求：
- 空队列 once 不唤醒
- 非空队列 once 会唤醒
- lock 已存在时返回 ok=false 或 skipped 状态
- cooldown 生效

完成后运行：
- uv run ruff format .
- uv run ruff check .
- uv run mypy src tests
- uv run pytest
```

---

## 9. Step 6: systemd user service 方案

### 目标

把 watcher 变成真正后台进程，而不是手动运行。

### 建议新增

```text
deploy/systemd/crypto-helper-queue-watcher.service
```

内容示例：

```ini
[Unit]
Description=Crypto Helper Queue Watcher
After=network.target openclaw-gateway.service

[Service]
Type=simple
WorkingDirectory=/home/zhmao/crypto_helper
ExecStart=uv run crypto-helper queue watch --poll-interval 2 --cooldown 5 --lock-ttl 60 --json
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### 注意

- 这个文件只是部署模板。
- 不要自动安装 systemd service，除非用户明确要求。
- 保留 OpenClaw cron 作为 fallback。

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后为 queue watcher 增加 systemd user service 模板。

要求：
1. 新增：
   - deploy/systemd/crypto-helper-queue-watcher.service
2. service 运行：
   - uv run crypto-helper queue watch --poll-interval 2 --cooldown 5 --lock-ttl 60 --json
3. 不自动安装 service。
4. 文档中说明安装命令，但不要执行：
   - systemctl --user enable ...
   - systemctl --user start ...
5. 保留 OpenClaw cron fallback 说明。

验证：
- uv run ruff check .
- 不需要运行 systemctl。
```

---

## 10. Step 7: 更新文档和 workspace

### 目标

让 `queue-dispatcher-agent` 和项目文档明确 V3 职责。

### 需要更新

```text
openclaw/workspaces/queue-dispatcher-agent/AGENTS.md
openclaw/workspaces/queue-dispatcher-agent/SOUL.md
openclaw/workspaces/queue-dispatcher-agent/TOOLS.md
openclaw/skills/queue-dispatcher/SKILL.md
openclaw/workspaces/queue-dispatcher-agent/skills/queue-dispatcher/SKILL.md
README.md
README.zh-CN.md
```

### 内容要点

- watcher 负责监听 pending queue。
- dispatcher 负责调用 dispatch-until-empty。
- worker result 回流 manager-agent。
- cron 是 fallback，不是主调度方式。
- dispatcher agent 不绑定 Discord / Telegram。

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后更新 queue watcher / dispatcher 文档。

要求：
1. 更新 queue-dispatcher-agent workspace 文档。
2. 更新 canonical queue-dispatcher skill 和 workspace skill copy。
3. 更新 README.md / README.zh-CN.md 的 async workflow 部分。
4. 明确：
   - queue watcher 只负责监听和唤醒
   - queue-dispatcher-agent 只负责调度
   - dispatch-until-empty 才负责批量消费
   - manager-agent 负责最终用户输出
   - cron 仅作为 fallback
5. 不写成内部运维手册。

验证：
- uv run ruff check .
```

---

## 11. Step 8: 端到端验证

### 目标

验证：

```text
pending 非空 -> watcher 唤醒 dispatcher -> dispatcher 清空队列 -> manager handoff 生成
```

### 手动验证命令

```bash
uv run crypto-helper queue enqueue-demo \
  --workflow-id kol_persona \
  --target-agent persona-runtime-agent \
  --kol KOL_A \
  --message "If BTC breaks 62000, what might this KOL infer?" \
  --json

uv run crypto-helper queue watch \
  --once \
  --poll-interval 1 \
  --cooldown 1 \
  --json

uv run crypto-helper queue list-pending --json
```

如果 V2 已实现：

```bash
uv run crypto-helper queue dispatch-until-empty --json
```

### 给 Codex 的 Prompt

```text
请先阅读 AGENTS.md，然后做 Queue Watcher V3 的端到端验证。

要求：
1. 入队至少 1 个 demo task。
2. 运行 queue watch --once --json。
3. 确认 watcher 发现 pending 非空并唤醒 dispatcher。
4. 确认 dispatcher 使用 dispatch-until-empty。
5. 确认 pending 变为空。
6. 确认 manager-agent handoff/result 已生成。

运行：
- uv run crypto-helper queue enqueue-demo ...
- uv run crypto-helper queue watch --once --json
- uv run crypto-helper queue list-pending --json
- uv run pytest

输出：
- watcher result
- dispatch result
- pending queue status
- known limitations
```

---

## 12. Cron fallback 策略

V3 后仍建议保留 cron，但降低其语义优先级。

推荐：

```text
watcher 是主触发器
cron 是兜底补偿
```

cron 可以每 5 分钟运行一次：

```text
Process the crypto_helper async delegation queue. Call crypto_helper_queue_dispatch_until_empty with max_tasks=10 and max_seconds=120. Return DispatchLoopResult only.
```

如果 watcher 正常，cron 大多数时候 no-op。

如果 watcher 停止，cron 会继续补偿处理 pending queue。

---

## 13. 最终 git 提交粒度

建议提交顺序：

```text
1. Add queue status helpers
2. Add queue watcher lock
3. Add OpenClaw dispatcher wake adapter
4. Add queue watch CLI
5. Add systemd queue watcher template
6. Document queue watcher runtime
```

每步提交前运行：

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

如涉及 plugin：

```bash
cd openclaw_plugin
npm install
npm run build
npm test
```

如涉及 OpenClaw runtime：

```bash
openclaw agents list --bindings
openclaw gateway status
```

---

## 14. 面试口径

可以这样讲：

```text
我把异步执行拆成三层。

第一层是 manager-agent，把复杂 workflow 入队。
第二层是 queue watcher，它作为后台进程监听 pending queue，发现非空就唤醒 queue-dispatcher-agent。
第三层是 dispatcher，它不让模型手动一条条循环，而是调用 Python 的 dispatch-until-empty，一次处理到队列为空或达到安全上限。

worker 完成后不会直接对用户输出，而是生成 manager handoff，回到 manager-agent 做最终响应。
这样既保留了 OpenClaw 多 Agent 编排，又把关键的循环、锁、失败处理放在可测试的 Python 代码里。
```

核心 tradeoff：

```text
watcher 降低延迟，cron 保留兜底；
watcher 不处理业务，避免重复消费和职责混乱；
真正的 queue claim / worker / finalize 仍由 Python orchestrator 保证一致性。
```
