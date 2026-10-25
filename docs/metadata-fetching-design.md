# 元数据获取架构升级方案（定稿）

> 状态：Approved / 已定稿（JavDB 声明式规则与 DMM 2K 封面升级已上线）  
> 背景：JavDB、AirAV、JavLibrary 等来源陆续启用或加强 Cloudflare 防护，同时站点局部 DOM 改版（如 JavDB 2026 演员节点改版）容易引发解析异常。本文確立“线上零 Token 声明式规则执行 + 字段级异常隔离 + 开发态智能体自愈维护 + 分层传输降级”的定稿方案。

## 结论先行

不建议把所有抓取都切换成无头浏览器或运行时大模型（Pure Agent Loop），也不建议继续在各站点 Parser 内零散添加“遇到 403 就启动浏览器”的补丁。

定稿采用分层、可降级、声明式的获取链路：

1. **声明式规则引擎 + 开发态智能体维护（线上零 Token）**：站点 XPath/CSS 与清洗规则抽离至 `src/scrapinglib/rules/*.json|.yaml` 随代码更新；线上保持毫秒级零成本执行，站点改版时由开发侧智能体抓包更新规则；
2. **字段级容错隔离（`_safe_extract`）**：非核心字段解析失败仅输出 `[parser_suspect]` 告警并降级为空值，绝不连坐清空整部影片结果；
3. **封面去水印与 2K 超清升级**：默认通过 `resolve_dmm_hd_cover` 优先探测 DMM AWS 官方 `2184×1468` 无水印原图，未命中则无缝回退站点自身封面；
4. **默认使用轻量 HTTP Transport（`curl_cffi`）**，仅在命中挑战页时按需升级 Browser Transport；
5. **统一识别限流、验证页、登录失效和页面结构变化（`parser_suspect`）**；
6. **逐步演进本地缓存与多来源字段级合并**。

浏览器后端首选 **Playwright**，因为浏览器生命周期、持久化 context、网络响应读取和跨平台支持比较完整；现有 **DrissionPage** 可以保留为适配器或短期过渡，避免一次性重写。最终选择应通过真实站点的小规模验证决定，而不是只比较“隐身”宣传。

## 当前实现梳理

当前主链路如下：

```text
scraper.get_data_from_json()
  -> scrapinglib.api.search()
    -> 按 priority.website 顺序动态加载 Parser
      -> Parser.scrape()/站点自定义 search()
        -> httprequest.get() 或 request_session()
        -> lxml/XPath 解析
      -> title、number 有效且至少存在一种封面即视为成功并停止
  -> 编号一致性校验、翻译、简繁转换、字段清洗
```

与 Cloudflare 相关的现状：

- `httprequest.get/post/request_session` 默认使用 `curl_cffi` 并模拟 Chrome TLS 指纹；
- 项目仍依赖 `cloudscraper`，目前主要用于 storyline 的 JavDB 路径；
- `javdb.py`、`airav.py`、`javlibrary.py` 各自判断 `403/503` 或页面中的 `Just a moment/请稍候`；
- 命中挑战后调用 `cf_bypass.auto_bypass_cloudflare()`，临时启动 headless DrissionPage；
- 浏览器成功打开页面后，将 Cookie 以 JSON 写到当前工作目录，再注入 `curl_cffi.Session` 重试；
- JavDB Cookie 通过文件修改时间粗略按 7 天判定有效，并支持多个镜像域名。

这套实现已经验证了“HTTP 快路径 + 浏览器兜底”的基本方向，但职责边界还没有形成。

## 当前风险和痛点

### 1. 反爬逻辑散落在站点 Parser

三个 Parser 都有近似的挑战检测、启动浏览器、加载 Cookie、再次请求逻辑。以后每增加一个站点或一种失败页面，都要复制修改，且行为很难保持一致。

### 2. Cookie 不等于浏览器会话

Cloudflare 放行状态可能与 IP、User-Agent、TLS/HTTP 指纹、域名及浏览器状态共同相关。DrissionPage 获取 Cookie 后换成 `curl_cffi` 请求，即使 Cookie 正确，也可能因为上下文不一致再次被拦截。因此需要支持“同一个浏览器 context 直接完成后续请求”，Cookie 转交只能算一次可尝试的优化。

### 3. 每次临时启动隐身浏览器，成本高且不稳定

当前浏览器使用 headless + incognito，最长等待约 25 秒，没有持久 profile、按域名的单飞锁或冷却时间。批量刮削时可能反复启动 Chromium，既慢，也会制造异常访问模式。

### 4. 失败类型被抹平

网络错误、429 限流、Cloudflare 验证、需要登录、影片不存在、XPath 失效，最后经常都变成 `{"title":""}` 或被宽泛的 `except` 吞掉。上层无法选择正确动作，也无法统计某个来源究竟是“没数据”还是“已经不可用”。

### 5. 配置没有完整贯穿请求层

- `request_session()` 接收 `retry`、`verify`、`ua`，但当前没有完整应用；
- `[proxy] timeout/retry` 没有统一传入各 Parser 的 session；
- 挑战识别只覆盖少量状态码和文案，未统一处理 429、重定向登录、200 状态挑战页等情况。

### 6. Cookie 文件存在安全和一致性风险

浏览器导出的 Cookie 默认写入当前工作目录，而仓库 `.gitignore` 没有覆盖站点 Cookie JSON。它们可能包含登录令牌，也可能被误提交。Cookie 的真实 `expires`、domain、来源 profile 和代理身份没有作为会话元数据管理，仅依赖文件 mtime 判断 7 天有效。

### 7. 来源策略仍是“依次试到第一个完整结果”

这会导致：

- 对已知失败来源重复请求；
- 一个来源缺少剧情或演员图时，不能自然地由其他来源补全；
- JavDB 既承担编号规范参考，又承担很多字段获取，故障影响被放大；
- 没有持久缓存，相同番号在整理、重试或补图时会重复抓取。

### 8. 缺少可回放测试

目前没有看到针对挑战页分类、搜索结果匹配、XPath 漂移和多来源合并的独立测试夹具。线上页面一变，往往只能靠一次真实刮削发现。

## 目标与非目标

### 目标

- 普通站点继续保持轻量、快速；
- 单个站点启用 Cloudflare 时，不拖垮整个刮削流程；
- 浏览器是可选依赖，CLI、Docker 和打包版本可明确选择是否携带；
- 能区分失败原因，支持退避、熔断、换源和人工介入；
- 尽量减少请求量，并能复用已获取的元数据；
- Parser 只负责“构造请求意图 + 解析内容”，不负责反爬策略。

### 非目标

- 不承诺自动通过所有 Cloudflare/CAPTCHA；
- 不做验证码识别、指纹伪造竞赛或无限代理轮换；
- 不绕过登录权限、付费权限和站点访问控制；
- 不保证某个外部站点永久可用；
- 应遵守来源站点条款、访问频率要求和适用法律。

## 建议架构

```text
Metadata Orchestrator
  ├─ Cache (raw response + normalized metadata)
  ├─ Source Policy (优先级、健康度、字段可信度、熔断)
  └─ Site Adapter
       ├─ Declarative Rule Manifest (src/scrapinglib/rules/*.json|.yaml，随代码更新，线上零 Token)
       ├─ Resolver: 番号 -> 详情页
       ├─ Parser: Response -> MetadataCandidate (字段级异常隔离 + parser_suspect 诊断)
       └─ Cover Upgrader: DMM AWS 2K 官方无水印原图优先 -> 站点封面回退
              |
         Fetch Client
           ├─ Response Classifier
           ├─ HTTP Transport (curl_cffi)
           └─ Browser Transport (Playwright / DrissionPage adapter)
                 └─ Session Store (按域名 + profile + proxy 隔离)
```

### Declarative Rule Engine & 开发态智能体维护（线上零 Token）

不建议在用户运行时对每次刮削调用大模型（Pure Agent Loop 耗时高、消耗大量 Token 且存在幻觉风险），而是采用 **“开发态智能体维护 + 线上确定性声明式规则执行”** 的混合架构：

1. **声明式规则配置（`src/scrapinglib/rules/{source}.json|.yaml`）**：
   - 将各站点的搜索 URL 模板、结果列表选择器、详情页各字段主备 XPath 列表、挑战页与登录墙特征词外置为声明式规则文件；
   - 随代码库维护更新，无需引入复杂的远端热更新服务或第三方运行期依赖。
2. **字段级异常隔离（Field-Level Fault Isolation）**：
   - `Parser.dictformat` 通过 `_safe_extract` 逐字段隔离提取异常；
   - 核心字段（`number`、`title`）校验失败才判定整站结果无效；非核心字段（如 `actor`、`runtime`、`trailer`）因站点局部 DOM 改版抛错时，输出 `[!] [parser_suspect] source=... field=...` 告警并降级为空值，绝不连坐清空整部影片元数据。
3. **开发态智能体快速修复**：
   - 当出现 `parser_suspect` 时，在开发侧通过智能体对实测样本抓包诊断，自动更新声明式规则文件并补充回归测试夹具（如 JavDB 2026 演员 `a.actor-female` 改版修复）。

### 封面去水印与超清升级策略（DMM 2K 原图优先 + 站点封面回退）

针对 JavDB 等站点封面可能带有水印或分辨率偏低（`800×538`）的问题，不再采用“为了换封面而重新完整爬取其他元数据站”的旧办法，而是采用 **DMM 官方 AWS 超清图床直推探测（`resolve_dmm_hd_cover`）**：

1. 将标准有码番号（如 `CAWB-012`、`FNS-152`）规范化为候选 DMM CID（`cawb00012`、`1fns00152` 等）；
2. 通过轻量 `HEAD` 请求优先探测 `https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{cid}/{cid}pl.jpg`（校验 HTTP 200、未重定向至 `now_printing` 且 `Content-Length >= 20KB`）；
3. 命中时直接升级为 **DMM 官方 `2184×1468`（2K 超清）无水印原图**；若非 DMM 体系影片或探测未命中，则无缝回退使用 JavDB 自身封面。

### Fetch Client：统一请求入口

站点代码不再直接管理 `curl_cffi.Session` 或启动浏览器，而是提交 `FetchRequest`：

```python
FetchRequest(
    url=url,
    source="javdb",
    purpose="search",       # search/detail/image/api
    preferred="http",
    allow_browser=True,
    session_key="javdb",
)
```

返回结构化 `FetchResult`：

```python
FetchResult(
    status="ok",            # ok/not_found/rate_limited/challenge/
                            # auth_required/transport_error/parser_suspect
    final_url="...",
    status_code=200,
    body="...",
    transport="http",
    elapsed_ms=123,
    attempts=1,
)
```

这样 Parser 可以明确表达“没有该番号”，Orchestrator 也能针对 `challenge` 升级浏览器、针对 `rate_limited` 退避、针对 `parser_suspect` 告警，而不是全部换源后静默失败。

### Response Classifier：把挑战识别集中起来

分类信号至少包括：

- HTTP 状态：401、403、429、503；
- 最终 URL 和重定向链：登录页、challenge path；
- HTML 标题和特征节点；
- Cloudflare 响应头或挑战脚本特征；
- 内容完整性：预期是 JSON 却收到 HTML、详情页缺少关键节点；
- Parser 版本/选择器与页面快照之间的不匹配。

分类器应保守：无法确认时返回 `unknown_block`，不要把挑战页当成“影片不存在”。站点可以提供额外规则，但升级决策由 Fetch Client 统一完成。

### HTTP Transport：继续作为默认快路径

保留 `curl_cffi`，但统一处理：

- timeout、connect/read retry、指数退避和 jitter；
- 429 的 `Retry-After`；
- 每域名并发和最小请求间隔；
- proxy、CA、headers、cookies 的一致传递；
- 请求/响应指标，但日志中必须脱敏 Cookie、Authorization 和代理凭据；
- GET 重试和非幂等请求重试策略分离。

不应在 HTTP 层无限重试挑战页。首次被明确分类为 challenge 后，立即交给策略层决定是否启用浏览器或换源。

### Browser Transport：按需、持久、可交互

建议能力：

- 每个站点使用持久化 user-data-dir，而不是 incognito；
- profile 与域名、代理出口绑定，避免跨站和跨代理混用状态；
- 同一域名只允许一个 challenge 恢复任务运行，其他任务等待结果；
- 优先复用已启动的 browser/context，并设置空闲回收时间；
- 支持 headless 常规执行，也支持显式 headed 模式让用户完成一次验证/登录；
- 验证后先在同一 browser context 内访问目标页；确认允许时，再尝试把会话同步给 HTTP Transport；
- 自动化无法继续时，返回 `manual_action_required`，不要死循环；
- 浏览器可执行文件、profile 和缓存目录均可配置。

建议用接口隔离具体实现：

```python
class BrowserTransport(Protocol):
    def fetch(self, request: FetchRequest) -> FetchResult: ...
    def ensure_session(self, session_key: str, interactive: bool) -> SessionState: ...
    def close_idle(self) -> None: ...
```

第一版可以只实现 Playwright；若现有 DrissionPage 在用户环境中更容易分发，则先将其包进同一接口，再用真实成功率和维护成本决定默认后端。

### Session Store：不要再把 Cookie 当作散落文件

建议默认存放在用户数据目录，例如 `~/.local/share/mdc/browser-profiles/`（Windows 使用对应的 AppData 目录），仓库工作目录不写认证材料。

Session 元数据至少记录：

- source/domain；
- browser backend 和 profile id；
- proxy identity（只记不可逆标识，不记密码）；
- User-Agent/browser version；
- Cookie 自带的 expiry 和最近一次验证时间；
- 最近成功、最近挑战、冷却截止时间。

同时立即将常见站点 Cookie 文件加入 `.gitignore`。如果未来需要加密存储，可接系统 keyring；第一阶段至少保证文件权限、日志脱敏和不进入仓库。

### Metadata Orchestrator：缓存、健康度与合并

建议将外站响应分成两级缓存：

1. **Raw cache**：站点原始 HTML/JSON，短 TTL，便于复现解析问题；
2. **Normalized cache**：标准化后的字段，较长 TTL，记录来源、抓取时间和 Parser 版本。

对同一番号的策略：

- 先返回仍在有效期内的标准化缓存；
- 需要刷新时按来源健康度和内容类型排序；
- 某来源连续 challenge/429 后进入短时熔断，不再对每个文件重复撞墙；
- 标题、番号、发行日等强字段做一致性校验；
- 封面、剧情、演员图、评分可按字段可信度从不同来源补齐；
- 保存每个字段的 provenance，便于排查和将来重算。

第一阶段仍可保持“第一个合格结果返回”，但接口和数据结构要允许后续字段级 merge，避免再重构一次。

## 浏览器方案取舍

| 方案                            | 优点                               | 缺点                                            | 建议定位                   |
| ------------------------------- | ---------------------------------- | ----------------------------------------------- | -------------------------- |
| 仅 `curl_cffi`                  | 快、轻、易打包                     | 无法处理需要 JS/交互的流程                      | 默认快路径                 |
| 当前 DrissionPage 临时取 Cookie | 已有代码、改动小                   | 临时进程、Cookie 转交不可靠、逻辑分散           | 短期过渡                   |
| Playwright 持久 context         | 生命周期和网络控制完整、跨平台成熟 | 浏览器体积大，PyInstaller/Docker 分发需单独处理 | 推荐 Browser Transport     |
| 外部浏览器守护进程/远端服务     | 主程序轻、会话可集中复用           | 部署复杂，远端服务还有隐私与成本问题            | 后续可选，不作为 MVP       |
| Selenium                        | 生态广、用户可能已有驱动           | 驱动和浏览器版本管理成本较高                    | 不优先，除非现有部署更适配 |

核心判断不是“哪个浏览器更像真人”，而是：能否稳定复用合法会话、能否在失败时让用户接管、是否易于观察和退出、打包部署成本是否可控。

## 推荐的升级顺序

### Phase 0：止血和可观测性

- Cookie 文件移出仓库目录并补 `.gitignore`；
- 定义错误枚举与 `FetchResult`，日志输出 source、阶段、状态和耗时；
- 集中 challenge 分类，JavDB/AirAV/JavLibrary 复用同一逻辑；
- 统一 timeout/retry/proxy/verify 配置传递；
- 为正常页、404、登录页、Cloudflare 页保存脱敏 fixture 并写分类测试；
- 为来源增加简单冷却：连续失败后若干分钟内直接换源。

这一步不换浏览器，也能显著降低“静默失败”和反复撞站。

### Phase 1：抽象 Transport

- 引入 `FetchClient`、`HttpTransport`、`ResponseClassifier`；
- 先迁移 JavDB，再迁移 AirAV/JavLibrary；
- Parser 只接收正文/结构化响应，不感知 Cloudflare；
- 对旧 Parser 保留兼容适配，避免一次改完全部来源。

### Phase 2：持久化 Browser Transport

- 实现 Playwright persistent context；
- 支持 `headless=auto/true/false`；
- 增加单飞锁、空闲回收、人工验证超时；
- 保证 challenge 后的第一次目标请求仍在浏览器 context 内完成；
- CLI/Docker/PyInstaller 分别给出“轻量版”和“browser extra”安装方式。

### Phase 3：缓存与字段级聚合

- 先上 SQLite normalized cache；
- 再增加 raw response 的限量、压缩、TTL 缓存；
- 为字段定义来源权重与冲突规则；
- 记录来源健康度，动态调整请求顺序；
- 增加离线 re-parse：页面解析器更新后，可用 raw cache 重跑而不访问站点。

## MVP 建议

首个可交付版本只聚焦 JavDB，范围控制为：

1. 新建统一 `FetchResult` 与错误分类；
2. 将 JavDB 的搜索页、详情页都切到 `FetchClient`；
3. HTTP 正常时行为与现在一致；
4. challenge 时只启动一个持久浏览器 context；
5. 若 headless 无法继续，输出明确提示，可配置打开 headed 浏览器供用户处理；
6. 成功页面保存短期缓存，同番号短时间重试不再次访问；
7. 用 fixture 覆盖正常搜索、无结果、challenge、详情 XPath 失效；
8. 保留 DrissionPage 旧路径作为一个版本周期的 feature flag 回退。

建议的模块边界（名称可调整）：

```text
src/fetching/
  models.py              # FetchRequest / FetchResult / FailureKind
  client.py              # 升级、退避、熔断策略
  classifier.py          # 通用 + 站点特征规则
  http_transport.py
  browser_transport.py
  session_store.py
  cache.py
```

## 配置草案

```ini
[fetch]
http_timeout = 20
http_retries = 2
per_host_interval = 2.0
cache = 1
cache_ttl_hours = 168
circuit_breaker_minutes = 15

[browser]
enabled = auto
backend = playwright
headless = auto
interactive_timeout = 120
idle_timeout = 300
profile_dir =

[source.javdb]
browser_fallback = 1
max_concurrency = 1
min_interval = 3.0
```

`auto` 的含义应是：安装了 browser extra 才允许升级；未安装时明确返回“浏览器后端不可用”，然后换源，而不是在运行中偷偷下载浏览器。

## 验收指标

不要只用“某次能打开 JavDB”作为验收。至少记录：

- 每来源请求成功率、challenge 率、429 率；
- HTTP 与 Browser 的请求数、耗时 P50/P95；
- 每 100 部影片启动浏览器的次数；
- cache hit rate；
- 完整元数据成功率和各字段缺失率；
- 因 `not_found`、`challenge`、`auth_required`、`parser_suspect` 失败的数量；
- browser profile 恢复成功率和需要人工操作的次数。

建议目标是“浏览器启动次数尽可能低、失败原因可解释、JavDB 故障时整体仍可用”，而不是追求 JavDB 单站 100% 自动化。

## 已敲定架构决策与上线状态

1. **智能体与大模型边界**：线上运行时**不强依赖大模型/不消耗 Token**，采用本地声明式规则（`src/scrapinglib/rules/*.json|.yaml`）随代码库直接更新，不引入复杂的在线规则热更新服务；智能体留在开发/维护侧用于抓包诊断与自动修复规则。
2. **字段级容错隔离**：已在 `Parser.dictformat` 中落地 `_safe_extract`，非核心字段失败输出 `[parser_suspect]` 告警而不清空整部影片元数据。
3. **JavDB 水印与封面策略**：已落地 **方案 1（DMM AWS 2K 官方无水印原图优先 + JavDB 封面回退）**，无需为了换封面去重复爬取其他站点。
4. **当前已上线范围（v1）**：
   - `.gitignore` 已屏蔽站点 Cookie JSON 文件；
   - `src/scrapinglib/rule_loader.py` 与 `src/scrapinglib/rules/javdb.json` 已上线；
   - `src/scrapinglib/javdb.py` 已完成声明式改造并修复 2026 演员 DOM 改版与时长清洗；
   - `tests/test_javdb_declarative.py` 回归测试夹具已上线并通过验证。
5. **后续演进阶段（按需启动）**：
   - 将其余高频站点（如 `javbus`、`airav`、`javlibrary`）逐步迁移至 `src/scrapinglib/rules/` 声明式规则；
   - 按 Phase 1/2 抽离跨站点共享的持久化 Browser Context 与 SQLite 缓存。
