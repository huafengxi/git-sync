# git-sync — 工作区多仓的周期性拉取守护（ff-only）

本仓只提供同步机制与独立 CLI。调用方拥有工作区、主机映射、服务声明、启动器、镜面钩子、端点和凭据；更换部署不应产生本仓 diff。无其它源码仓依赖，不要求统一平台或 sibling 目录。

## 是什么

工作区（一个主仓 + 若干子仓）的周期性代码拉取守护：每 `--interval` 秒（缺省 60）对每个仓做 `git pull --ff-only`。判定序、日志形态与红线的权威 = `git-sync.py` 的 docstring。

- **同步面自动发现**：顶层含 `.git` 且被主仓 `.gitignore` 排除的目录即入面；`--repos` 覆盖。逐候选 `check-ignore`，斜杠形态失败再询问无斜杠形态；无法分类只 WARN 并排除该候选，不令整张面降级。
- **输出面只有日志**：一条结果一行，由调用方重定向；不写协议文件、不读 `pid.json`、与 agent 树零耦合。锁住 `<workspace>/run/locks/git-sync.lock` 保证单实例。
- **镜像保鲜**：宿主判据 = `is_mirror_host()`（镜面目录下有 `*.git` 目录即是），镜面来自目录发现，无机器名或名单。后台线程 + 每镜像超时，上一轮未完则跳过、不排队。镜面 fetch 不 force；非 ff 只 WARN，不覆盖分叉。回推上游由调用方的事件钩子承担，不在本进程内。
- 工作树脏/本地未推提交只跳过；SKIP 日志 `behind=N` 表示未带回的上游提交规模。不会替调用方 merge、reset 或强推。

## 根解析与使用

独立源码目录可任意命名。源码身份按 `realpath`（含软链入口），默认工作区是源码仓的父目录，与 cwd 无关；非空 `PLATFORM_WORKSPACE` 覆盖，展开 `~` 并绝对化，相对值相对调用 cwd。`--root` 优先于该环境变量。固定 release 目录的调用方应显式注入真实工作区，不依赖默认父目录。

```bash
python3 /path/to/git-sync/git-sync.py --help
PLATFORM_WORKSPACE=/path/to/workspace python3 /path/to/git-sync/git-sync.py --once
python3 /path/to/git-sync/git-sync.py --once --root /path/to/test-workspace --repos .
```

`--mirror-dir` 缺省 `~/git`，仅在根等于解析出的默认根且未给 `--repos` 时启用镜面 fetch。指定其它 `--root` 或给出 `--repos` 可隔离镜面；**与默认根相同的显式 `--root` 本身不构成镜面禁用开关**（继承原行为）。测试应同时指定自建 workspace/mirror fixture，或使用 `--repos`，不要把生产根传给测试。

源码的运行需求是 Python 标准库（含 POSIX `fcntl`）与 Git；没有常驻 shell 包装，也不依赖 Bash 扩展。调用方负责监督、日志重定向与启停；本源码交付不安装服务、不切换任何现网引用。

## 隔离验证

```bash
# TMPDIR、HOME 应指向调用方新建的隔离测试目录；测试保留 fixture 不做清理。
python3 test_git_sync.py
python3 test_platform_paths.py
python3 test_recovery.py
bash test_shell_entry.sh /absolute/path/to/python3  # 可用真实 Bash 3.2 执行
```

原 `test_git_sync.py` 的发现/dirty/ahead/分叉/ff-only/CLI/镜面发现回归继承自原 main；全部 fetch/pull 仅访问自建本地 bare fixture。新增恢复测试覆盖真实镜面 ff 成功/非 ff 拒绝、线程不重叠、超时、独立根/空格/不同 cwd/真实和软链入口及缺本地 helper 拒绝。测试不访问真实模型、生产镜面或服务，也不递归删除 fixture。

发现面本身的补丁不能靠已降级的发现面自动送达；若源码目录已退出同步面，调用方须另行更新该目录并通过自身启动器重启。历史与源码投影、共享 helper 来源及适配见 [recovery/ADAPTATION.md](recovery/ADAPTATION.md)。
