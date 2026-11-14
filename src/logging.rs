//! Bounded diagnostic logging. User libraries never belong in logs.
//! Preserve the legacy log path across the GoreeCloud Notes display-name transition.
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, OnceLock};

const MAX_FILE_BYTES: u64 = 1024 * 1024;
const MAX_STDERR_BYTES: u64 = 1024 * 1024;
const MAX_LINE_BYTES: usize = 4096;
const TRUNCATED: &str = " …[truncated]";
static FILE: OnceLock<Mutex<LogFile>> = OnceLock::new();
static OPENED: OnceLock<PathBuf> = OnceLock::new();
static STDERR_USED: AtomicU64 = AtomicU64::new(0);

struct LogFile {
    file: File,
    written: u64,
}

/// Keep established paths while users move from GoreeCloud Rich Text Editor to GoreeCloud Notes.
pub fn dir() -> PathBuf {
    if let Some(d) = std::env::var_os("GOREECLOUD_RTE_LOG_DIR") { return PathBuf::from(d) }
    #[cfg(target_os = "macos")]
    let base = dirs::home_dir().map(|h| h.join("Library").join("Logs").join("goreecloud-rich-text-editor"));
    #[cfg(not(target_os = "macos"))]
    let base = dirs::data_local_dir().map(|d| d.join("goreecloud-rich-text-editor").join("logs"));
    base.unwrap_or_else(|| std::env::temp_dir().join("goreecloud-rich-text-editor-logs"))
}

/// The file actually written (the temp fallback included).
pub fn path() -> PathBuf {
    OPENED.get().cloned().unwrap_or_else(|| dir().join("goreecloud-rich-text-editor.log"))
}

struct Logger;

impl log::Log for Logger {
    fn enabled(&self, m: &log::Metadata) -> bool {
        m.level() <= log::Level::Warn || m.target().starts_with("goreecloud_rich_text_editor")
    }
    fn log(&self, r: &log::Record) {
        if self.enabled(r.metadata()) { write(&format!("{} {}: {}", r.level(), r.target(), r.args())); }
    }
    fn flush(&self) {}
}

fn limit_line(line: &str) -> String {
    if line.len() <= MAX_LINE_BYTES { return line.to_owned(); }
    let mut end = MAX_LINE_BYTES - TRUNCATED.len();
    while !line.is_char_boundary(end) { end -= 1; }
    format!("{}{}", &line[..end], TRUNCATED)
}

fn write_bounded<W: Write>(out: &mut W, used: &mut u64, line: &str) -> io::Result<()> {
    if *used >= MAX_FILE_BYTES { return Ok(()); }
    let bytes = line.as_bytes();
    if (*used).saturating_add(bytes.len() as u64) > MAX_FILE_BYTES {
        const MARKER: &[u8] = b"[log limit reached; remaining records omitted until restart]\n";
        if (*used).saturating_add(MARKER.len() as u64) <= MAX_FILE_BYTES {
            out.write_all(MARKER)?;
        }
        *used = MAX_FILE_BYTES;
        return Ok(());
    }
    out.write_all(bytes)?;
    *used += bytes.len() as u64;
    Ok(())
}

/// A large existing log is truncated at startup, not renamed to an unlimited
/// .old.log. Keep bounded diagnostics within the application's own directory.
fn open_log(dir: PathBuf) -> io::Result<(LogFile, PathBuf)> {
    std::fs::create_dir_all(&dir)?;
    let p = dir.join("goreecloud-rich-text-editor.log");
    let mut file = OpenOptions::new().create(true).append(true).open(&p)?;
    let mut len = file.metadata()?.len();
    if len >= MAX_FILE_BYTES {
        file.set_len(0)?;
        len = 0;
    }
    Ok((LogFile { file, written: len }, p))
}

/// Install early for launch failures. Log-to-disk and stderr output are bounded
/// for the lifetime of this process; logging failures do not block startup.
pub fn init() {
    let opened = open_log(dir()).or_else(|_| open_log(std::env::temp_dir().join("goreecloud-rich-text-editor-logs")));
    if let Ok((file, p)) = opened {
        let _ = OPENED.set(p);
        let _ = FILE.set(Mutex::new(file));
    }
    let _ = log::set_logger(&Logger).map(|()| log::set_max_level(log::LevelFilter::Info));
    let default = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        write(&format!("PANIC {info}\n{}", std::backtrace::Backtrace::force_capture()));
        default(info);
    }));
    let exe = std::env::current_exe().map(|p| p.display().to_string()).unwrap_or_default();
    write(&format!("start GoreeCloud Notes {} ({exe})", env!("CARGO_PKG_VERSION")));
}

/// Maximum 4 KiB per record, 1 MiB to stderr and 1 MiB to the managed file.
/// Does not intercept third-party writes directly to stdout/stderr.
pub fn write(line: &str) {
    let bounded = limit_line(line);
    let n = bounded.len() as u64 + 1;
    let can_emit = STDERR_USED.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
        |used| (used.saturating_add(n) <= MAX_STDERR_BYTES).then_some(used + n)).is_ok();
    if can_emit { eprintln!("{bounded}"); }
    let Some(state) = FILE.get() else { return };
    let Ok(mut state) = state.lock() else { return };
    let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs()).unwrap_or(0);
    let record = format!("[{secs}] {bounded}\n");
    let LogFile { file, written } = &mut *state;
    let _ = write_bounded(file, written, &record);
    if *written < MAX_FILE_BYTES { let _ = file.flush(); }
}

/// A launch that cannot continue: logged, shown (Windows has no console),
/// exit code 1.
pub fn fatal(what: &str, err: &anyhow::Error) -> ! {
    write(&format!("ERROR {what}: {err:#} (log: {})", path().display()));
    #[cfg(target_os = "windows")]
    {
        let text = format!("{what}\n\n{err:#}\n\n日志 / Log: {}", path().display());
        let wide = |s: &str| s.encode_utf16().chain(Some(0)).collect::<Vec<u16>>();
        #[link(name = "user32")]
        unsafe extern "system" { fn MessageBoxW(hwnd: *mut std::ffi::c_void, text: *const u16, caption: *const u16, kind: u32) -> i32; }
        // MB_OK | MB_ICONERROR
        unsafe { MessageBoxW(std::ptr::null_mut(), wide(&text).as_ptr(), wide("GoreeCloud Rich Text Editor").as_ptr(), 0x10); }
    }
    std::process::exit(1)
}

#[cfg(test)]
mod bounded_log_tests {
    use super::*;
    #[test]
    fn utf8_records_are_capped_without_breaking_char_boundaries() {
        let huge = "📔".repeat(5000);
        let short = limit_line(&huge);
        assert!(short.len() <= MAX_LINE_BYTES);
        assert!(short.ends_with(TRUNCATED));
        assert!(short.is_char_boundary(short.len()));
        assert_eq!(limit_line("hello"), "hello");
    }

    #[test]
    fn sustained_errors_cannot_exceed_1mib_file_budget() {
        let mut out = Vec::new();
        let mut written = 0;
        let repeated = format!("{}\n", "e".repeat(4095));
        for _ in 0..2000 {
            write_bounded(&mut out, &mut written, &repeated).unwrap();
        }
        assert!(out.len() <= MAX_FILE_BYTES as usize);
        assert_eq!(written, MAX_FILE_BYTES);
        let original_len = out.len();
        write_bounded(&mut out, &mut written, "ignored\n").unwrap();
        assert_eq!(out.len(), original_len);
    }
}
