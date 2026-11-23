/**
 * dsh-roadshow-copilot — host-side plugin.
 *
 * The plugin ships the roadshow-copilot skill bundle (SKILL.md + scripts +
 * Python vendor libs) inside the package and installs it into the user's DSH
 * skill directory on startup. DSH's filesystem skill provider then lists it in
 * the session catalog automatically — no restart needed once files land.
 *
 * Large assets (the 465 MB Whisper model) are NOT bundled; the skill downloads
 * them on first use via its scripts/dl.py.
 */
import { access, cp, mkdir, readFile, writeFile } from 'node:fs/promises'
import { constants } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'roadshow-copilot'
export const inject = []

const here = dirname(fileURLToPath(import.meta.url))
const packageRoot = join(here, '..')
const SKILL_NAME = 'roadshow-copilot'

function dshHome() {
  return process.env.DSH_HOME || join(homedir(), '.dsh')
}

async function readVersion() {
  try {
    const raw = await readFile(join(packageRoot, 'package.json'), 'utf8')
    return JSON.parse(raw).version || '0.0.0'
  } catch {
    return '0.0.0'
  }
}

async function exists(path) {
  try {
    await access(path, constants.F_OK)
    return true
  } catch {
    return false
  }
}

export async function apply(ctx, config = {}) {
  const log = ctx?.logger ?? console
  const target = config.skillDir || join(dshHome(), 'skills', SKILL_NAME)
  const source = join(packageRoot, 'skill')
  const stampPath = join(target, '.plugin-version')
  const version = await readVersion()

  try {
    const stamp = (await exists(stampPath)) ? (await readFile(stampPath, 'utf8')).trim() : ''
    if (stamp === version) {
      log.debug?.(`[${name}] skill ${version} already installed at ${target}`)
      return
    }
    await mkdir(target, { recursive: true })
    await cp(source, target, { recursive: true, force: true })
    await writeFile(stampPath, version, 'utf8')
    log.info?.(`[${name}] installed skill ${version} -> ${target}`)
  } catch (error) {
    // Never take the host down because a skill copy failed.
    log.warn?.(`[${name}] failed to install skill into ${target}: ${error?.message ?? error}`)
  }
}
