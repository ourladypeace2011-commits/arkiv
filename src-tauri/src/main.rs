// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;

struct ServerProcess(Mutex<Option<Child>>);

fn main() {
    // Start the arkiv-server sidecar (PyInstaller binary)
    let sidecar_path = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.join("arkiv-server")))
        .expect("Cannot determine sidecar path");

    let child = if sidecar_path.exists() {
        Some(
            Command::new(&sidecar_path)
                .spawn()
                .expect("Failed to start arkiv-server sidecar"),
        )
    } else {
        eprintln!(
            "Warning: sidecar not found at {:?}, assuming server is already running",
            sidecar_path
        );
        None
    };

    tauri::Builder::default()
        .manage(ServerProcess(Mutex::new(child)))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill the sidecar when the window closes
                if let Some(state) = window.try_state::<ServerProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
