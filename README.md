# free-nodes

定时抓取公开免费节点源 → 去重 → TCP 测活 → 生成一份**你自己控制的固定订阅地址**。

抓到的节点是别人公开分享的，随时会失效；这个仓库的作用是**每天自动帮你换一批**，你只订阅一次就不用管了。

## 目录

```
.
├─ .github/workflows/update.yml   每 6 小时自动跑
├─ scripts/collect.py             抓取 + 去重 + 测活 + 生成订阅
├─ sources.txt                    订阅源列表(改这里)
└─ output/                        自动生成的产物, 不要手改
   ├─ sub.txt        明文节点, 每行一个
   ├─ sub_b64.txt    base64 订阅(NekoBox/v2rayNG 用这个)
   └─ stats.json     本次统计
```

## 部署(5 步)

1. GitHub 新建一个**公开**仓库（私有仓库的 raw 地址需要 token，客户端不好用）
2. 把本目录所有文件传上去（网页上传、或 `git push` 都行）
3. 仓库 **Settings → Actions → General → Workflow permissions** 选 **Read and write permissions**，保存
4. **Actions** 标签页 → 左侧 `update-free-nodes` → **Run workflow** 手动跑一次
5. 跑完 `output/` 里会有文件，你的订阅地址就是：

```
https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/output/sub_b64.txt
```

## 导入 NekoBox

1. NekoBox → 左上 **☰** → 新建分组
2. 类型选 **Subscription / 订阅**
3. URL 填上面的 raw 地址
4. 自动更新间隔填 `6`（小时）
5. 保存 → 回主界面 **⋮ → 更新当前组订阅**
6. **⋮ → URL Test** 测一遍，再 **清理不可用配置**

## 调整

- **加源**：往 `sources.txt` 加一行 URL。加完先自己打开看一眼那个源是否还在更新。
- **改频率**：`update.yml` 里的 `cron: "17 */6 * * *"`，`*/6` 是每 6 小时。注意 GitHub 定时任务在高峰期可能延迟，且仓库 60 天无提交会自动停掉定时（本仓库有自动提交，不受影响）。
- **测活更严格**：`collect.py` 顶部 `TEST_TIMEOUT = 3.0`，调大能滤掉更多假活，但会漏掉慢节点。
- **只要协议子集**：在 `LINK_RE` 里删掉不要的协议名即可。

## 需要知道的

- 这里的「测活」是 **TCP 端口连通性**，不是「能不能翻墙」。连得上不等于能用，最终还得靠 NekoBox 里的 URL Test。
- GitHub Actions 公开仓库免费额度足够（一次跑约 1–3 分钟）。
- raw 地址有 CDN 缓存（约 5 分钟），刚跑完看不到新内容属正常。
- 这些节点由陌生人提供，服务端能看到你的流量。**不要用它登录银行、支付、主邮箱**。
