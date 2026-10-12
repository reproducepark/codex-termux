use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    let object = out.join("atomic-probe.o");
    let library = out.join("libatomic_probe.a");
    assert!(
        Command::new(env::var_os("CC_aarch64_linux_android").unwrap())
            .args(["-O2", "-fPIC", "-c", "atomic-probe.c", "-o"])
            .arg(&object)
            .status()
            .unwrap()
            .success()
    );
    assert!(
        Command::new(env::var_os("AR_aarch64_linux_android").unwrap())
            .arg("crs")
            .arg(&library)
            .arg(&object)
            .status()
            .unwrap()
            .success()
    );
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=atomic_probe");
    println!("cargo:rerun-if-changed=atomic-probe.c");
}
