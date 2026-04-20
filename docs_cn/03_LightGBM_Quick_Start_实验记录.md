# LightGBM Quick Start 实验记录

> **实验日期**：2026-04-20  
> **实验环境**：Windows 11，conda 环境 `qlib`，Python 3.9  
> **实验目标**：跑通 Qlib README 中的 LightGBM Quick Start 演示，记录每步操作和结果

---

## 一、实验背景

### 1.1 什么是这个 Demo？

Qlib README 中的 Quick Start 以 **LightGBM + Alpha158 因子集 + CSI300 股票池** 为例，展示了一个完整的量化研究工作流：

1. 从 Qlib 数据库加载 A 股行情数据
2. 构建 Alpha158 特征集（158 个因子，基于日线 OHLCV 通过表达式引擎计算）
3. 训练 LightGBM 模型预测股票未来收益
4. 对预测信号进行回测（TopkDropout 策略，沪深 300 股票池）
5. 输出 IC、IR、年化超额收益等评估指标

### 1.2 数据说明

- **股票池**：CSI300（沪深 300 指数成分股，动态调整）
- **基准指数**：SH000300（沪深 300 指数）
- **训练区间**：2008-01-01 至 2014-12-31（7 年）
- **验证区间**：2015-01-01 至 2016-12-31（2 年）
- **测试区间**：2017-01-01 至 2020-08-01（约 3.5 年）
- **数据来源**：community 数据源（chenditc/investment_data，2026-04-19 版本，522.7 MB）

### 1.3 模型说明：LightGBM

LightGBM（Light Gradient Boosting Machine，Guolin Ke et al., NIPS 2017）是微软开发的高效 GBDT 框架，具备：
- **基于直方图的决策树**：训练速度快于 XGBoost
- **Leaf-wise 生长策略**：比 Level-wise 更精准
- **支持缺失值**：适合金融数据（有停牌等缺失情况）

在 Qlib 中，`LGBModel` 封装于 `qlib/contrib/model/gbdt.py`，以均方误差（MSE）为损失函数预测股票未来收益率。

---

## 二、环境配置步骤

### Step 1：克隆仓库

```powershell
cd D:\vscode_project
git clone https://github.com/dxZJU/qlib.git
# 输出：Cloning into 'qlib'...（成功）
```

### Step 2：创建并激活 conda 环境

```powershell
conda create -n qlib python=3.9 -y
conda activate qlib
```

**执行结果**：
- 环境创建成功：`qlib` (Python 3.9)
- 注意：初次从源码安装时遇到 `Microsoft Visual C++ 14.0 or greater is required` 错误，Cython 扩展（`greenlet` 等）需要 MSVC 编译器

### Step 3：安装 Qlib（改用 PyPI 预编译 wheel）

由于 Windows 环境未安装 Visual C++ Build Tools，改用 PyPI 发布的预编译包：

```powershell
pip install numpy cython -q
pip install pyqlib -q    # 使用 PyPI 预编译版本，跳过 C 扩展编译
```

> **说明**：`pyqlib` 为 Qlib 在 PyPI 上的发布名称，等价于从 pypi.org 安装稳定版，包含预编译 Windows wheel，无需 MSVC。

### Step 4：下载数据

由于官方数据集暂时下线，使用社区数据源：

```powershell
# 下载（522.7 MB，2026-04-19 版本）
$url = "https://github.com/chenditc/investment_data/releases/download/2026-04-19/qlib_bin.tar.gz"
$dest = "$env:USERPROFILE\.qlib\qlib_data\qlib_bin.tar.gz"
Start-BitsTransfer -Source $url -Destination $dest   # 下载完成：522.7 MB ✓

# 解压
python -c "
import tarfile, os
with tarfile.open(os.path.expanduser(r'~\.qlib\qlib_data\qlib_bin.tar.gz'), 'r:gz') as t:
    t.extractall(os.path.expanduser(r'~\.qlib\qlib_data\cn_data'), ...)
"
```

**解压后目录结构**：
```
~/.qlib/qlib_data/cn_data/
├── calendars/day.txt        # 交易日历
├── instruments/             # 股票池（csi300, csi500, all 等）
└── features/                # 每只股票的 OHLCV.bin 文件
```

---

## 三、运行 LightGBM Demo

### Step 5：切换到 examples 目录并运行

```powershell
cd D:\vscode_project\qlib\examples
qrun benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml
```

> **重要**：必须在 `examples/` 目录下运行，不能在含有 `qlib/` 子包的父目录下运行，否则 Python 会优先加载本地 `qlib/` 目录而非安装包，导致模块导入混乱。

### Step 6：工作流配置文件解读

运行的配置文件为 `benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`，内容如下：

```yaml
qlib_init:
  provider_uri: "~/.qlib/qlib_data/cn_data"   # 数据路径
  region: cn                                    # A 股模式

market: &market csi300                          # 股票池：沪深 300
benchmark: &benchmark SH000300                  # 基准：沪深 300 指数

data_handler_config: &data_handler_config
  start_time: 2008-01-01
  end_time: 2020-08-01
  fit_start_time: 2008-01-01
  fit_end_time: 2014-12-31                      # 用训练集 fit 归一化参数
  instruments: *market

task:
  model:
    class: LGBModel                             # LightGBM 模型
    kwargs:
      loss: mse
      colsample_bytree: 0.8879                  # 列采样比例
      learning_rate: 0.2
      subsample: 0.8789                         # 行采样比例
      lambda_l1: 205.6999                       # L1 正则
      lambda_l2: 580.9768                       # L2 正则
      max_depth: 8
      num_leaves: 210
      num_threads: 20

  dataset:
    class: DatasetH
    kwargs:
      handler:
        class: Alpha158                         # 158 个因子
      segments:
        train: [2008-01-01, 2014-12-31]
        valid: [2015-01-01, 2016-12-31]
        test:  [2017-01-01, 2020-08-01]

  record:
    - class: SignalRecord       # 保存模型预测信号
    - class: SigAnaRecord       # 信号分析（IC, IR 等）
    - class: PortAnaRecord      # 组合分析（回测）
      kwargs:
        config: *port_analysis_config           # TopkDropout 策略，top50，n_drop=5
```

### Step 7：工作流执行过程

`qrun` 执行时经历以下阶段（以下均为实际日志）：

#### 阶段 1：数据加载与特征计算

```
[22:43:23] qlib successfully initialized based on client settings.
[22:43:23] data_path={'__DEFAULT_FREQ': WindowsPath('C:/Users/twenty/.qlib/qlib_data/cn_data')}
[22:44:49] Time cost: 83.227s | Loading data Done
[22:44:50] Time cost: 0.295s | DropnaLabel Done
[22:44:52] Time cost: 2.785s | CSZScoreNorm Done
[22:44:53] Time cost: 3.548s | fit & process data Done
[22:44:53] Time cost: 86.776s | Init data Done
```

> **耗时约 87 秒**，计算 CSI300 成分股 2008–2020 年的 Alpha158 因子（约 158 列特征）。

#### 阶段 2：LightGBM 模型训练

```
Training until validation scores don't improve for 50 rounds
[20]    train's l2: 0.980543    valid's l2: 0.993487
[40]    train's l2: 0.972654    valid's l2: 0.993893
[60]    train's l2: 0.965936    valid's l2: 0.994966
Early stopping, best iteration is:
[23]    train's l2: 0.979172    valid's l2: 0.993376
```

> **Early stopping 在第 23 轮触发**（验证集 l2 = 0.9934），远早于最大 1000 轮。训练集 l2 持续下降，而验证集从第 23 轮后开始上升，说明发生了过拟合。

#### 阶段 3：信号预测（前 5 行示例）

```
'The following are prediction results of the LGBModel model.'
                      score
datetime   instrument
2017-01-03 SH600000   -0.022016
           SH600005   -0.100878
           SH600008    0.010251
           SH600009    0.034503
           SH600010   -0.025966
```

> 预测信号（`score`）表示模型对该股票相对收益的预测，正值为预测跑赢、负值为预测跑输。

#### 阶段 4：信号分析（SigAnaRecord）

```python
{'IC': np.float64(0.04703019872499099),
 'ICIR': np.float64(0.3816414521971541),
 'Rank IC': np.float64(0.04869434960382118),
 'Rank ICIR': np.float64(0.4056898351502206)}
```

#### 阶段 5：回测（PortAnaRecord）

```
[22:45:09] Create new exchange
```

---

## 四、实验结果

### 4.1 预期结果（来自 Qlib 官方文档）

```
'The following are analysis results of the excess return without cost.'
                       risk
mean               0.000708
std                0.005626
annualized_return  0.178316
information_ratio  1.996555
max_drawdown      -0.081806

'The following are analysis results of the excess return with cost.'
                       risk
mean               0.000512
std                0.005626
annualized_return  0.128982
information_ratio  1.444287
max_drawdown      -0.091078
```

### 4.2 实际运行结果（本次实验实测）

> **运行时间**：2026-04-20 22:43:23 → 22:46:33，**总耗时约 3 分 10 秒**

#### 信号分析（SigAnaRecord）

| 指标 | 实测值 | 说明 |
|------|--------|------|
| IC（信息系数）均值 | **0.0470** | 预测值与真实收益的 Pearson 相关系数 |
| ICIR（信息比率）| **0.3816** | IC均值 / IC标准差 |
| Rank IC 均值 | **0.0487** | Spearman 秩相关 |
| Rank ICIR | **0.4057** | Rank IC 的稳定性指标 |

#### 基准收益分析（SH000300 沪深300基准）

| 指标 | 实测值 | 说明 |
|------|--------|------|
| 日均收益（mean）| 0.000477 | 日均基准收益率 |
| 年化收益 | **11.36%** | 基准年化收益 |
| 信息比率（IR）| 0.599 | 基准夏普类指标 |
| 最大回撤 | **-37.05%** | 测试期基准自身最大回撤（2017-2020含2018熊市） |

#### 超额收益分析（不计成本）

```
'The following are analysis results of the excess return without cost(1day).'
                       risk
mean               0.000619
std                0.005496
annualized_return  0.147334
information_ratio  1.737630
max_drawdown      -0.078346
```

| 指标 | 实测值 | 说明 |
|------|--------|------|
| 日均超额收益（mean） | 0.000619 | 日均 0.062% 的超额收益 |
| 年化超额收益 | **14.73%** | 相对沪深300，策略每年多赚约 14.7% |
| 信息比率（IR）| **1.7376** | 风险调整后超额收益，> 1 说明策略稳健 |
| 最大回撤 | -7.83% | 策略相对基准最差情况下损失约 7.8% |

#### 超额收益分析（计入成本）

```
'The following are analysis results of the excess return with cost(1day).'
                       risk
mean               0.000465
std                0.005494
annualized_return  0.110624
information_ratio  1.305132
max_drawdown      -0.085821
```

| 指标 | 实测值 | 说明 |
|------|--------|------|
| 年化超额收益（含成本）| **11.06%** | 扣除交易成本后 |
| 信息比率（含成本）| **1.3051** | 仍 > 1，策略仍具价值 |
| 最大回撤（含成本）| -8.58% | 成本略微放大回撤 |

#### 与官方预期结果对比

| 指标 | **本次实测** | 官方 README 预期 | 差异 |
|------|------------|-----------------|------|
| 年化超额收益（不含成本）| 14.73% | 17.83% | -3.1pp |
| IR（不含成本）| 1.7376 | 1.9966 | -0.26 |
| 最大回撤（不含成本）| -7.83% | -8.18% | 低 0.35pp（更小）|
| 年化超额收益（含成本）| 11.06% | 12.90% | -1.84pp |
| IR（含成本）| 1.3051 | 1.4443 | -0.14 |

> **差异原因**：官方数据为 Yahoo Finance 来源；本次使用 chenditc 社区数据（2026-04-19 版本），数据来源不同导致因子值存在细微差异，但整体趋势与官方结果高度一致。

---

## 五、结果解读

### 5.1 训练过程解读

- **Early stopping 在第 23 轮触发**（设定 early_stopping_rounds=50）：验证集 l2 从第 23 轮（0.9934）开始持续上升（40轮0.9939，60轮0.9950），说明模型在较少的树数量下已学到主要规律
- **train l2 持续下降**：说明模型仍有拟合能力，过拟合发生在训练集/验证集之间
- **L2 在 0.98–0.99 左右**：由于标签经过跨截面 Z-Score 归一化（方差为1），L2 接近 1.0 是正常的（难以预测的低信噪比问题）

### 5.2 信号质量解读

- **IC = 0.047**：接近量化业界 "有价值信号" 门槛（> 0.03–0.05），意味着预测值与真实收益每天平均有 4.7% 的线性相关
- **ICIR = 0.38**：IC 较稳定但仍有波动（理想 ICIR > 0.5），说明模型在某些市场环境下效果较弱
- **Rank IC ≈ IC**：线性和秩相关接近，说明信号的单调性较好

### 5.3 组合绩效解读

- **年化超额收益 14.73%（不含成本）**：策略显著跑赢沪深 300，每年超额约 14.7%
- **IR = 1.74**：> 1 通常认为策略稳健可靠，接近 2.0 是量化策略中较高水平
- **最大回撤 -7.83%**：相对基准回撤小，2018 年大熊市期间策略仍能保持超额收益
- **含成本后 IR 从 1.74 降至 1.31**：成本对策略有显著影响（降低约 25%），TopkDropout 每日调仓换手率较高，实盘中需注意控制换手

### 5.4 关键结论

1. ✅ **Demo 成功跑通**：从数据加载、模型训练、信号生成到回测分析全链路运行正常
2. ✅ **结果与官方基本一致**：超额收益年化 11–15%，IR > 1.3，与 README 预期值差距在合理范围内
3. ⚠️ **数据来源影响结果**：社区数据与官方数据存在细微差异，若追求与基准完全一致，需使用相同来源数据
4. ⚠️ **Early stopping 过早**：仅第 23 轮即停止，说明数据量相对于模型复杂度较小，或超参数有优化空间

### 5.3 与官方结果的一致性

本次运行结果与 Qlib 官方文档中的预期结果基本一致（数据来源不同可能导致小幅差异），说明 Demo 已成功跑通。

---

## 六、操作命令汇总

```powershell
# 1. 激活环境
conda activate qlib

# 2. 进入 examples 目录（重要！）
cd D:\vscode_project\qlib\examples

# 3. 运行 LightGBM Demo
qrun benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml

# 4. 查看实验结果（MLflow UI）
cd D:\vscode_project\qlib
mlflow ui
# 在浏览器打开 http://127.0.0.1:5000 查看实验记录
```

---

## 七、常见报错与解决

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `ModuleNotFoundError: No module named 'qlib'` | 环境未激活 | `conda activate qlib` |
| `FileNotFoundError: cn_data not found` | 数据路径错误 | 检查 `provider_uri` 设置 |
| `KeyError: csi300` | instruments 文件缺失 | 确认数据完整下载，检查 `instruments/csi300.txt` |
| `Microsoft Visual C++ 14.0 required` | 从源码安装遇到编译问题 | 改用 `pip install pyqlib`（预编译 wheel）|
| `ImportError: cannot import name 'ops'` | 在 qlib 父目录下运行 | `cd examples` 后再运行 `qrun` |
