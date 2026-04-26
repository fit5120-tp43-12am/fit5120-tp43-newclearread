const fs = require('fs')
const http = require('http')
const path = require('path')

const port = process.env.PORT || 8080
const rootDir = __dirname
const versionPattern = /^version[\w.-]*$/

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
}

function send(res, statusCode, body, contentType = 'text/plain; charset=utf-8') {
  res.writeHead(statusCode, { 'Content-Type': contentType })
  res.end(body)
}

function redirect(res, location) {
  res.writeHead(302, { Location: location })
  res.end()
}

function getAvailableVersions() {
  return fs
    .readdirSync(rootDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && versionPattern.test(entry.name))
    .map((entry) => entry.name)
    .sort()
}

function getDefaultVersion() {
  const configuredVersion = process.env.DEFAULT_VERSION
  if (configuredVersion && versionPattern.test(configuredVersion)) {
    return configuredVersion
  }

  return getAvailableVersions()[0] || 'version1'
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase()
  const contentType = contentTypes[ext] || 'application/octet-stream'

  fs.createReadStream(filePath)
    .on('error', () => send(res, 500, 'Internal server error'))
    .once('open', () => {
      res.writeHead(200, { 'Content-Type': contentType })
    })
    .pipe(res)
}

function handleVersionRequest(req, res, pathname, version) {
  const versionRoot = path.join(rootDir, version)

  if (!fs.existsSync(versionRoot) || !fs.statSync(versionRoot).isDirectory()) {
    send(res, 404, 'Version not found')
    return
  }

  if (pathname === `/${version}`) {
    redirect(res, `/${version}/`)
    return
  }

  const relativePath = decodeURIComponent(pathname.slice(version.length + 2)) || 'index.html'
  const requestedPath = path.normalize(path.join(versionRoot, relativePath))

  if (requestedPath !== versionRoot && !requestedPath.startsWith(`${versionRoot}${path.sep}`)) {
    send(res, 403, 'Forbidden')
    return
  }

  if (fs.existsSync(requestedPath) && fs.statSync(requestedPath).isFile()) {
    sendFile(res, requestedPath)
    return
  }

  if (path.extname(relativePath)) {
    send(res, 404, 'Not found')
    return
  }

  sendFile(res, path.join(versionRoot, 'index.html'))
}

const server = http.createServer((req, res) => {
  const { pathname } = new URL(req.url, `http://${req.headers.host}`)

  if (pathname === '/') {
    redirect(res, `/${getDefaultVersion()}/`)
    return
  }

  const version = pathname.split('/').filter(Boolean)[0]
  if (version && versionPattern.test(version)) {
    handleVersionRequest(req, res, pathname, version)
    return
  }

  send(res, 404, 'Not found')
})

server.listen(port, () => {
  console.log(`Versioned static server listening on port ${port}`)
})
