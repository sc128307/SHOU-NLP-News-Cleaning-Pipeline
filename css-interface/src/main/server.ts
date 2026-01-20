import express from 'express'
import cors from 'cors'
import fs from 'fs'
import path from 'path'
import { shell, dialog, BrowserWindow } from 'electron'

let mainWindowRef: BrowserWindow | null = null
let reviewDir: string | null = null

export function setMainWindow(win: BrowserWindow) {
  mainWindowRef = win
}
export function setReviewDir(dir: string) {
  reviewDir = dir
}

// 辅助函数：处理 CSV 行，考虑引号包裹的逗号
function splitCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]

    if (char === '"') {
      inQuotes = !inQuotes // 切换引号状态
    } else if (char === ',' && !inQuotes) {
      // 只有不在引号内遇到的逗号，才是分隔符
      result.push(current.trim()) // 去掉两端空格
      current = ''
    } else {
      current += char
    }
  }
  result.push(current.trim()) // 推入最后一列

  // 清理引号：如果字段是被双引号包围的，去掉它们
  return result.map((col) => {
    if (col.startsWith('"') && col.endsWith('"')) {
      return col.slice(1, -1).replace(/""/g, '"') // 处理转义引号
    }
    return col
  })
}

// --- 核心辅助函数：解析 CSV ---
function parseProgressCSV(csvPath: string) {
  try {
    if (!fs.existsSync(csvPath)) return { stats: { total: 0, checked: 0, percent: 0 }, fileMap: {} }
    const content = fs.readFileSync(csvPath, 'utf-8')
    const lines = content.split('\n').filter((line) => line.trim() !== '')
    if (lines.length < 2) return { stats: { total: 0, checked: 0, percent: 0 }, fileMap: {} }

    const headers = splitCsvLine(lines[0])
    const filenameIdx = headers.findIndex((h) => h.trim() === 'Filename')
    const checkedIdx = headers.findIndex((h) => h.trim() === 'Checked')

    let checkedCount = 0
    const fileMap: Record<string, string> = {}

    for (let i = 1; i < lines.length; i++) {
      const cols = splitCsvLine(lines[i])
      const isChecked = checkedIdx !== -1 && cols[checkedIdx] && cols[checkedIdx].trim() === 'Yes'
      if (isChecked) checkedCount++
      if (filenameIdx !== -1 && cols[filenameIdx]) {
        fileMap[cols[filenameIdx].trim()] = isChecked ? 'Yes' : 'No'
      }
    }
    const total = lines.length - 1
    const percent = total > 0 ? Math.round((checkedCount / total) * 100) : 0
    return { stats: { total, checked: checkedCount, percent }, fileMap }
  } catch (e) {
    return { stats: { total: 0, checked: 0, percent: 0 }, fileMap: {} }
  }
}

// --- 核心逻辑：判断是否为任务文件夹，并读取进度 ---
function getTaskInfo(dirPath: string) {
  // 策略：先看自己是不是任务，再看 output 子目录是不是任务
  let targetJson = path.join(dirPath, 'frontend_diff.json')
  let targetCsv = path.join(dirPath, 'progress_log.csv')

  // 检查 output 子目录模式
  if (!fs.existsSync(targetJson)) {
    const subOutput = path.join(dirPath, 'output')
    if (fs.existsSync(subOutput) && fs.statSync(subOutput).isDirectory()) {
      targetJson = path.join(subOutput, 'frontend_diff.json')
      targetCsv = path.join(subOutput, 'progress_log.csv')
    }
  }

  if (fs.existsSync(targetJson)) {
    let stats = { total: 0, checked: 0, percent: 0 }
    if (fs.existsSync(targetCsv)) {
      const parsed = parseProgressCSV(targetCsv)
      stats = parsed.stats
    }
    return {
      isTask: true,
      isContainer: false, // 是任务就不是容器
      jsonPath: targetJson,
      csvPath: targetCsv,
      stats
    }
  }

  return { isTask: false, ...getContainerStats(dirPath) }
}

// [新增] 辅助函数：统计容器文件夹内的子任务进度
function getContainerStats(dirPath: string) {
  try {
    const subItems = fs.readdirSync(dirPath, { withFileTypes: true })
    let totalTasks = 0
    let completedTasks = 0

    for (const item of subItems) {
      if (item.isDirectory()) {
        const fullPath = path.join(dirPath, item.name)
        // 复用 getTaskInfo 检查子文件夹是不是一个任务
        const info = getTaskInfo(fullPath)
        if (info.isTask) {
          totalTasks++
          // 如果任务总数 > 0 且 已检查数 == 总数，视为完成
          if (info.stats && info.stats.total > 0 && info.stats.checked === info.stats.total) {
            completedTasks++
          }
        }
      }
    }

    if (totalTasks > 0) {
      return {
        isContainer: true,
        stats: {
          total: totalTasks,
          checked: completedTasks,
          percent: Math.round((completedTasks / totalTasks) * 100)
        }
      }
    }
  } catch (e) {
    // ignore error
  }
  return { isContainer: false, stats: null }
}

export function startServer(port = 3333) {
  const app = express()
  app.use(cors())
  app.use(express.json())

  // [新增] 1. 配置静态文件服务
  // 如果是在开发环境运行 ts，可能需要指向源码目录；如果是打包后，需要指向资源目录。
  // 为了稳健，我们可以尝试多个路径或者硬编码一个相对于 app 的路径
  const staticPath = path.join(__dirname, '../../www') // 根据你的实际目录结构调整层级

  if (fs.existsSync(staticPath)) {
    app.use(express.static(staticPath))
    console.log(`Serving static files from: ${staticPath}`)
  } else {
    console.error(`Static folder not found at: ${staticPath}`)
  }

  // [新增] 根路由 - 确保访问 http://localhost:3333 时返回 index.html
  app.get('/', (req, res) => {
    const indexPath = path.join(staticPath, 'index.html')
    if (fs.existsSync(indexPath)) {
      res.sendFile(indexPath)
    } else {
      res.send('Review Lab HTML not found. Please check server configuration.')
    }
  })

  // 1. List Directory (用于看板)
  app.post('/api/list-directory', (req, res) => {
    const { currentPath } = req.body
    if (!currentPath || !fs.existsSync(currentPath)) return res.json({ items: [], parent: null })

    try {
      // 1. 计算上一级目录 (修复灰色箭头问题)
      const parent = path.dirname(currentPath)
      // 防止回退到磁盘根目录之上 (比如 D:\ 的 parent 还是 D:\)
      const safeParent = parent !== currentPath ? parent : null
      const dirents = fs.readdirSync(currentPath, { withFileTypes: true })
      const items = dirents
        .filter((dirent) => dirent.isDirectory())
        .map((dirent) => {
          const fullPath = path.join(currentPath, dirent.name)
          const info = getTaskInfo(fullPath)

          return {
            name: dirent.name,
            path: fullPath,
            isTask: info.isTask,
            isContainer: info.isContainer || false, // 新增状态
            progress: info.stats || { total: 0, checked: 0, percent: 0 }
          }
        })

      // 返回 items 和 parent
      res.json({ items, parent: safeParent })
    } catch (e) {
      res.status(500).json({ error: String(e) })
    }
  })

  // 2. Get Files (用于编辑器) - 逻辑修正
  app.post('/api/get-files', (req, res) => {
    const { dir } = req.body
    if (!dir || !fs.existsSync(dir)) return res.json([])

    // 使用 getTaskInfo 智能定位 json 文件
    const info = getTaskInfo(dir)

    if (!info.isTask || !info.jsonPath) {
      // 没找到任务数据
      return res.json([])
    }

    const results: any[] = []
    try {
      // 读取 CSV 获取审核状态
      const { fileMap } = parseProgressCSV(info.csvPath!)

      // 读取 JSON 获取内容
      const fileContent = fs.readFileSync(info.jsonPath, 'utf-8')
      const diffData = JSON.parse(fileContent)

      diffData.forEach((item: any) => {
        let filename = item.filename
        let isChecked = 'No'
        if (fileMap && fileMap[filename]) isChecked = fileMap[filename]

        results.push({
          id: filename,
          original: item.original_text,
          cleaned: item.cleaned_body,
          highlights: item.highlights,
          metadata: item.metadata,
          folder: path.basename(dir),
          checked: isChecked
        })
      })
    } catch (e) {
      console.error('Error reading diff json:', e)
    }
    res.json(results)
  })

  // 3. Save File (保存逻辑)
  app.post('/api/save-file', (req, res) => {
    const { dir, fileId, status, content } = req.body
    const info = getTaskInfo(dir) // 再次使用智能定位

    if (!info.isTask) return res.status(400).json({ error: 'Not a task directory' })

    // 既然找到了 json，说明这一层(或output子层)就是我们要写的目录
    const targetDir = path.dirname(info.jsonPath!)
    const csvPath = path.join(targetDir, 'progress_log.csv')
    const txtPath = path.join(targetDir, fileId)

    try {
      if (content !== undefined) {
        // 完全信任前端
        // 前端编辑器现在负责维护整个文件的 XML 结构 (<title>, <date>, <body> 等)。
        // 后端不再尝试解析或拼接，直接覆盖写入文件即可。
        fs.writeFileSync(txtPath, content, 'utf-8')
      }

      const newStatus = status ? status.trim() : 'Yes'
      // 更新 CSV 状态
      if (fs.existsSync(csvPath)) {
        let csvContent = fs.readFileSync(csvPath, 'utf-8')
        const lines = csvContent.split(/\r?\n/)

        // 寻找表头
        let headerIndex = -1
        let filenameIdx = -1
        let checkedIdx = -1

        // 扫描前几行找表头
        for (let i = 0; i < Math.min(lines.length, 5); i++) {
          const cols = splitCsvLine(lines[i]) // <--- 使用智能分割
          const fIdx = cols.findIndex((c) => c === 'Filename')
          const cIdx = cols.findIndex((c) => c === 'Checked')

          if (fIdx !== -1 && cIdx !== -1) {
            headerIndex = i
            filenameIdx = fIdx
            checkedIdx = cIdx
            break
          }
        }

        if (filenameIdx !== -1 && checkedIdx !== -1) {
          const newLines = lines.map((line, index) => {
            if (index <= headerIndex || !line.trim()) return line

            // 最稳妥的方法：解析 -> 修改 -> 重新序列化 (CSV Stringify)
            const cols = splitCsvLine(line)

            if (cols[filenameIdx] === fileId) {
              // 找到目标行

              // 补齐列
              while (cols.length <= checkedIdx) cols.push('')
              cols[checkedIdx] = newStatus

              // 重新组合成 CSV 行 (处理引号)
              return cols
                .map((col) => {
                  // 如果包含逗号或引号，需要包起来
                  if (col.includes(',') || col.includes('"')) {
                    return `"${col.replace(/"/g, '""')}"`
                  }
                  return col
                })
                .join(',')
            }
            return line
          })

          fs.writeFileSync(csvPath, newLines.join('\n'), 'utf-8')
        }
      }

      res.json({ success: true, status: newStatus })
    } catch (e: any) {
      console.error('Save failed:', e)
      res.status(500).json({ error: e.message })
    }
  })

  // 3.5 Skip File (跳过/删除文件)
  app.post('/api/skip-file', (req, res) => {
    const { dir, fileId } = req.body
    const info = getTaskInfo(dir)

    if (!info.isTask) return res.status(400).json({ error: 'Not a task directory' })

    const targetDir = path.dirname(info.jsonPath!)
    const csvPath = path.join(targetDir, 'progress_log.csv')

    try {
      if (fs.existsSync(csvPath)) {
        let csvContent = fs.readFileSync(csvPath, 'utf-8')
        // 处理 BOM
        if (csvContent.charCodeAt(0) === 0xfeff) csvContent = csvContent.slice(1)

        const lines = csvContent.split(/\r?\n/)

        // 1. 寻找表头
        let headerIndex = -1
        let filenameIdx = -1

        for (let i = 0; i < Math.min(lines.length, 5); i++) {
          const cols = splitCsvLine(lines[i])
          const fIdx = cols.findIndex((c) => c === 'Filename')
          if (fIdx !== -1) {
            headerIndex = i
            filenameIdx = fIdx
            break
          }
        }

        if (filenameIdx !== -1) {
          // 2. 过滤掉目标行
          const newLines = lines.filter((line, index) => {
            // 保留表头
            if (index <= headerIndex) return true
            // 过滤空行
            if (!line.trim()) return false

            const cols = splitCsvLine(line)
            const currentFilename = cols[filenameIdx] ? cols[filenameIdx].trim() : ''

            // 如果文件名匹配，就删除（返回 false）
            return currentFilename !== fileId
          })

          fs.writeFileSync(csvPath, newLines.join('\n'), 'utf-8')
          res.json({ success: true })
        } else {
          res.status(500).json({ error: 'CSV Header not found' })
        }
      } else {
        res.status(404).json({ error: 'CSV not found' })
      }
    } catch (e: any) {
      console.error('Skip failed:', e)
      res.status(500).json({ error: e.message })
    }
  })

  // 4. Remote Control
  app.post('/api/request-run', (req, res) => {
    const { dir } = req.body
    if (mainWindowRef) {
      mainWindowRef.webContents.send('auto-fill-task', dir)
      if (mainWindowRef.isMinimized()) mainWindowRef.restore()
      mainWindowRef.focus()
      res.json({ success: true })
    } else {
      res.status(500).json({ error: 'Window not found' })
    }
  })

  // 5. 浏览器请求打开本地文件夹选择框
  app.post('/api/choose-directory', async (req, res) => {
    try {
      // 在 Electron 主进程中打开原生对话框
      // mainWindowRef 是可选参数，如果不传，对话框会独立浮动
      const result = await dialog.showOpenDialog(mainWindowRef || undefined, {
        properties: ['openDirectory'],
        title: 'Select Corpus Root Directory'
      })

      if (result.canceled || result.filePaths.length === 0) {
        return res.json({ success: false, path: null })
      }

      // 将选中的绝对路径返回给浏览器
      res.json({ success: true, path: result.filePaths[0] })
    } catch (error: any) {
      console.error('Dialog error:', error)
      res.status(500).json({ error: error.message })
    }
  })

  const serverInstance = app.listen(port, () => {
    console.log(`Local server running on http://127.0.0.1:${port}`)
  })
  return serverInstance
}
