use std::fs::File;
use std::fs::TryLockError;
use std::process::Command;

unsafe extern "C" {
    fn termux_atomic_probe() -> i32;
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    assert_eq!(unsafe { termux_atomic_probe() }, 0);
    let args: Vec<_> = std::env::args().collect();
    let file = File::options()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(&args[1])?;
    if let Some(mode) = args.get(2) {
        let result = match mode.as_str() {
            "exclusive" => file.try_lock(),
            "shared" => file.try_lock_shared(),
            _ => panic!("unknown lock mode"),
        };
        match result {
            Ok(()) => return Ok(()),
            Err(TryLockError::WouldBlock) => std::process::exit(23),
            Err(TryLockError::Error(error)) => return Err(error.into()),
        }
    }
    let child = |mode: &str| -> Result<Option<i32>, std::io::Error> {
        Ok(Command::new(std::env::current_exe()?)
            .args([&args[1], mode])
            .status()?
            .code())
    };
    file.lock()?;
    assert_eq!(child("exclusive")?, Some(23));
    assert_eq!(child("shared")?, Some(23));
    file.unlock()?;
    assert_eq!(child("exclusive")?, Some(0));
    file.lock_shared()?;
    assert_eq!(child("shared")?, Some(0));
    assert_eq!(child("exclusive")?, Some(23));
    file.unlock()?;
    file.try_lock()?;
    file.unlock()?;
    file.try_lock_shared()?;
    file.unlock()?;
    println!(
        "PASS Android std::fs locks and NDK atomics: exclusive/shared contention, blocking acquisition, unlock"
    );
    Ok(())
}
