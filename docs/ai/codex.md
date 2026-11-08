# Codex 环境约定

本文适用于 Codex 环境。使用子代理时另读[模型选择约定](codex-subagent-model-selection.md)。

## 沙箱权限与命令拆分

按当前会话的权限配置安排操作。本项目默认环境为：

- 文件系统：工作区可写，`.git` 与工作区外目录只读，`/tmp` 可写。
- Socket：TCP/UDP 的创建、连接与 send/sendall/sendto 受限，包括回环地址。Unix socketpair 可以创建，send 仍可能返回 EPERM；继承的已连接描述符可通过 read/write、sendmsg/recvmsg 收发。
- 事件循环和进程间通信可能受上述限制而挂起。检查须设置有限超时，清理自有子进程；确认由沙箱引起时，按审批机制在沙箱外执行同一检查。

受限命令须独立调用，每次只做一件事。例如 git add、git commit 及后续 git status 分别调用；多个受限命令也须逐个提交。此要求适用于已有批准、首次执行与权限失败后的重试；每次审批应能明确对应单项操作。

以下每个代码块分别作为一次命令调用，检查前一步结果后继续；提交说明与文件列表按任务填写：

```sh
git add AGENTS.md
```

```sh
git commit -m "docs: update collaboration guidelines"
```

```sh
git status --short
```

全部操作都在沙箱允许范围内时，可以按需组合，例如 `cat README.md && rg -n 'Codex' AGENTS.md`。将受限命令与其他操作放入同一次调用，包括通过 `&&`、`;`、管道、换行或脚本包装组合，须符合下述特殊情况。

## 特殊情况的沙箱外执行申请

确有必要合并受限命令与其他操作时，以 `sandbox_permissions: "require_escalated"` 提交申请，在 justification 中：

- 明确标注“特殊情况”。
- 说明必须合并、无法拆分的原因。
- 解释整段命令的用途、每项操作及影响范围。

执行前须取得覆盖该整段命令的批准。一般权限批准仍按单项操作使用；便利或减少工具调用次数不足以构成合并理由。
