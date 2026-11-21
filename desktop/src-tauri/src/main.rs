// Tavola desktop: a thin Tauri shell around the Python core.
//
// First launch finds or downloads `uv`, creates a private Python runtime,
// installs the released Tavola wheel, and runs `tavola serve` on localhost.
// Settings stay in ~/.tavola.yaml; nothing is sent anywhere except the model
// provider the user configures.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager, RunEvent, State};

const TAVOLA_VERSION: &str = env!("CARGO_PKG_VERSION");
const TAVOLA_WHEEL_URL: &str =
    "https://github.com/michael-borck/tavola/releases/download/v0.1.0/tavola-0.1.0-py3-none-any.whl";

struct Sidecar(Mutex<Option<Child>>);

#[derive(Serialize, Deserialize, Default, Clone)]
struct Settings {
    provider: String,
    base_url: String,
    api_key: String,
    model: String,
}

fn status(app: &AppHandle, message: &str) {
    let _ = app.emit("status", message.to_string());
}

fn config_path() -> Result<PathBuf, String> {
    dirs::home_dir()
        .map(|home| home.join(".tavola.yaml"))
        .ok_or_else(|| "Could not determine home directory".into())
}

fn yaml_str(value: &serde_yaml::Value, key: &str) -> String {
    value
        .get(key)
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_string()
}

#[tauri::command]
fn get_settings() -> Settings {
    let Ok(path) = config_path() else {
        return Settings::default();
    };
    let Ok(text) = fs::read_to_string(&path) else {
        return Settings::default();
    };
    let Ok(root) = serde_yaml::from_str::<serde_yaml::Value>(&text) else {
        return Settings::default();
    };

    let provider = yaml_str(&root, "llm");
    let mut settings = Settings {
        provider: provider.clone(),
        base_url: yaml_str(&root, "base_url"),
        api_key: yaml_str(&root, "api_key"),
        model: yaml_str(&root, "model"),
    };
    if let Some(overlay) = root.get("llms").and_then(|p| p.get(&provider)) {
        for (field, key) in [
            (&mut settings.base_url, "base_url"),
            (&mut settings.api_key, "api_key"),
            (&mut settings.model, "model"),
        ] {
            let value = yaml_str(overlay, key);
            if !value.is_empty() {
                *field = value;
            }
        }
    }
    settings
}

#[tauri::command]
fn save_settings(settings: Settings) -> Result<(), String> {
    if settings.provider.is_empty() {
        return Err("Pick a provider".into());
    }
    let path = config_path()?;
    let mut root = if path.exists() {
        let text = fs::read_to_string(&path)
            .map_err(|e| format!("Could not read {}: {e}", path.display()))?;
        serde_yaml::from_str::<serde_yaml::Value>(&text)
            .map_err(|e| format!("Could not parse {}: {e}", path.display()))?
    } else {
        serde_yaml::Value::Mapping(Default::default())
    };
    let serde_yaml::Value::Mapping(map) = &mut root else {
        return Err(format!(
            "{} is not a YAML mapping; edit it by hand",
            path.display()
        ));
    };

    map.insert("llm".into(), settings.provider.clone().into());
    for key in ["base_url", "api_key", "model"] {
        map.remove(key);
    }
    let llms = map
        .entry("llms".into())
        .or_insert(serde_yaml::Value::Mapping(Default::default()));
    if !llms.is_mapping() {
        *llms = serde_yaml::Value::Mapping(Default::default());
    }
    if let serde_yaml::Value::Mapping(llms) = llms {
        let mut block = match llms.get(&settings.provider) {
            Some(serde_yaml::Value::Mapping(m)) => m.clone(),
            _ => serde_yaml::Mapping::new(),
        };
        for (key, value) in [
            ("base_url", &settings.base_url),
            ("api_key", &settings.api_key),
            ("model", &settings.model),
        ] {
            if value.is_empty() {
                block.remove(key);
            } else {
                block.insert(key.into(), value.clone().into());
            }
        }
        llms.insert(settings.provider.clone().into(), block.into());
    }

    let text = serde_yaml::to_string(&root).map_err(|e| e.to_string())?;
    fs::write(&path, text).map_err(|e| e.to_string())?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = fs::set_permissions(&path, fs::Permissions::from_mode(0o600));
    }
    Ok(())
}

fn command(program: impl AsRef<std::ffi::OsStr>) -> Command {
    let cmd = Command::new(program);
    #[cfg(windows)]
    let cmd = {
        use std::os::windows::process::CommandExt;
        let mut c = cmd;
        c.creation_flags(0x0800_0000);
        c
    };
    cmd
}

fn run_ok(cmd: &mut Command) -> Result<(), String> {
    let output = cmd.output().map_err(|e| e.to_string())?;
    if output.status.success() {
        Ok(())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    }
}

fn find_uv() -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Some(home) = dirs::home_dir() {
        candidates.push(home.join(".local/bin/uv"));
        candidates.push(home.join(".cargo/bin/uv"));
    }
    candidates.push("/opt/homebrew/bin/uv".into());
    candidates.push("/usr/local/bin/uv".into());
    #[cfg(windows)]
    if let Some(home) = dirs::home_dir() {
        candidates.push(home.join(".local\\bin\\uv.exe"));
    }
    for path in candidates {
        if path.exists() {
            return Some(path);
        }
    }
    let probe = command("uv").arg("--version").output();
    if matches!(probe, Ok(ref o) if o.status.success()) {
        return Some("uv".into());
    }
    None
}

fn install_uv(app: &AppHandle) -> Result<PathBuf, String> {
    status(app, "Downloading uv (one-time)…");
    #[cfg(not(windows))]
    run_ok(command("sh").args(["-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]))?;
    #[cfg(windows)]
    run_ok(command("powershell").args([
        "-NoProfile",
        "-ExecutionPolicy",
        "ByPass",
        "-Command",
        "irm https://astral.sh/uv/install.ps1 | iex",
    ]))?;
    find_uv().ok_or_else(|| "uv installed but not found".into())
}

fn tavola_bin(venv: &Path) -> PathBuf {
    #[cfg(windows)]
    return venv.join("Scripts").join("tavola.exe");
    #[cfg(not(windows))]
    venv.join("bin").join("tavola")
}

fn venv_python(venv: &Path) -> PathBuf {
    #[cfg(windows)]
    return venv.join("Scripts").join("python.exe");
    #[cfg(not(windows))]
    venv.join("bin").join("python")
}

fn ensure_runtime(app: &AppHandle, force_update: bool) -> Result<PathBuf, String> {
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;
    let venv = data_dir.join("runtime");
    let bin = tavola_bin(&venv);
    let marker = venv.join("tavola-version");
    let installed = fs::read_to_string(&marker).unwrap_or_default();
    if bin.exists() && installed.trim() == TAVOLA_VERSION && !force_update {
        return Ok(bin);
    }

    let uv = match find_uv() {
        Some(uv) => uv,
        None => install_uv(app)?,
    };
    if !venv.exists() {
        status(app, "Setting up Python runtime (one-time, ~a minute)…");
        run_ok(command(&uv).args(["venv", "--python", "3.12"]).arg(&venv))?;
    }
    status(app, "Installing Tavola…");
    let dev_path = std::env::var("TAVOLA_DEV_PATH").ok();
    if let Some(path) = dev_path {
        run_ok(
            command(&uv)
                .args(["pip", "install", "--upgrade", "--python"])
                .arg(venv_python(&venv))
                .arg(format!("-e {path}[serve,render]")),
        )?;
    } else {
        run_ok(
            command(&uv)
                .args(["pip", "install", "--upgrade", "--python"])
                .arg(venv_python(&venv))
                .arg(format!("tavola[serve,render] @ {TAVOLA_WHEEL_URL}")),
        )?;
    }
    status(app, "Installing Chromium for PNG/PDF export (one-time)…");
    run_ok(command(venv_python(&venv)).args(["-m", "playwright", "install", "chromium"]))?;
    let _ = fs::write(&marker, TAVOLA_VERSION);
    Ok(bin)
}

fn free_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|e| e.to_string())?;
    Ok(listener.local_addr().map_err(|e| e.to_string())?.port())
}

fn kill_sidecar(sidecar: &Sidecar) {
    if let Ok(mut guard) = sidecar.0.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn spawn_sidecar(app: &AppHandle, bin: &Path) -> Result<u16, String> {
    let port = free_port()?;
    let out_dir = dirs::picture_dir()
        .or_else(dirs::home_dir)
        .unwrap_or_else(|| ".".into())
        .join("Tavola");

    status(app, "Starting Tavola…");
    let mut cmd = command(bin);
    cmd.args([
        "serve",
        "--host",
        "127.0.0.1",
        "--port",
        &port.to_string(),
        "--out-dir",
    ])
    .arg(&out_dir)
    .args(["--parent-pid", &std::process::id().to_string()])
    .stdin(Stdio::piped());
    if let Ok(data_dir) = app.path().app_data_dir() {
        cmd.current_dir(data_dir);
    }
    let child = cmd
        .spawn()
        .map_err(|e| format!("Could not start tavola: {e}"))?;

    let sidecar: State<Sidecar> = app.state();
    kill_sidecar(&sidecar);
    *sidecar.0.lock().unwrap() = Some(child);

    let deadline = Instant::now() + Duration::from_secs(30);
    let addr = format!("127.0.0.1:{port}");
    loop {
        if TcpStream::connect(&addr).is_ok() {
            std::thread::sleep(Duration::from_millis(300));
            return Ok(port);
        }
        if Instant::now() > deadline {
            return Err("Tavola server did not come up within 30s".into());
        }
        std::thread::sleep(Duration::from_millis(200));
    }
}

#[tauri::command]
async fn start_server(app: AppHandle, update: bool) -> Result<u16, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let bin = ensure_runtime(&app, update)?;
        spawn_sidecar(&app, &bin)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn restart_server(app: AppHandle) -> Result<u16, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let bin = ensure_runtime(&app, false)?;
        spawn_sidecar(&app, &bin)
    })
    .await
    .map_err(|e| e.to_string())?
}

fn main() {
    tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            get_settings,
            save_settings,
            start_server,
            restart_server
        ])
        .build(tauri::generate_context!())
        .expect("error while building Tavola")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                kill_sidecar(&app.state::<Sidecar>());
            }
        });
}
