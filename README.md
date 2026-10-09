# JobTrack

使用 Python、FastAPI 和 SQLite 记录求职申请，并使用 pytest 测试接口。

## 本地运行（Windows PowerShell）

需要 Python 3.10 或以上版本。在项目目录执行以下命令。

首次运行时创建虚拟环境；已有 `.venv` 可以跳过创建步骤：

```powershell
python -m venv .venv
```

激活环境并安装依赖：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

初始化数据库并启动服务：

```powershell
python init_db.py
python -m uvicorn main:app --reload
```

`init_db.py` 会在当前目录创建 `jobtrack.db` 和申请表；已有表时不会删除数据。
请始终从项目目录运行服务，因为数据库路径是相对路径。

打开 http://127.0.0.1:8000/docs 查看接口并发送请求。
在运行服务的终端按 `Ctrl+C` 停止服务。

## 接口

| 方法 | 路径 | 用途 | 成功状态码 |
| --- | --- | --- | --- |
| GET | `/health` | 检查服务是否运行 | 200 |
| POST | `/applications` | 新增申请 | 201 |
| GET | `/applications` | 查看、筛选、分页 | 200 |
| GET | `/applications/{application_id}` | 查看一条申请 | 200 |
| PATCH | `/applications/{application_id}` | 修改申请状态 | 200 |
| DELETE | `/applications/{application_id}` | 删除申请，返回空响应 | 204 |

新增申请的 JSON 请求正文：

```json
{
  "company": "Acme",
  "position": "Python Developer"
}
```

新增后状态为 `applied`，返回的数据包含数据库生成的 `id`。
公司名和职位名会去除两端空白，不允许为空，最多分别为 100 和 150 个字符。

修改状态的 JSON 请求正文：

```json
{
  "status": "interview"
}
```

合法状态：`applied`、`interview`、`offer`、`rejected`。

列表支持组合查询参数，例如：

```text
/applications?company=Acme&status=interview&limit=10&offset=0
```

`company` 按公司名匹配；`status` 按状态匹配。结果按 ID 升序排列。
`limit` 表示最多返回多少条，默认 20，允许 1 到 100。
`offset` 表示跳过多少条，默认 0，不允许负数。

找不到申请返回 `404`，请求数据不符合要求返回 `422`。

## 测试

激活虚拟环境后，在项目目录执行：

```powershell
python -m pytest -q
```

测试使用独立的临时数据库，不修改本地 `jobtrack.db`。

## 文件

- `main.py`：接口、输入输出模型、校验和数据库操作。
- `init_db.py`：初始化数据库。
- `test_main.py`：接口测试。
- `requirements.txt`：需要安装的 Python 包。
- `.gitignore`：让 Git 忽略虚拟环境、缓存和本地数据库。

本地数据库不提交到 Git。新环境通过 `init_db.py` 创建数据库。
