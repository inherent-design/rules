
pub fn base() -> (ProjectIntent, ResolutionLock) { fixture() }
pub fn key_of(s: &str) -> DependencyKey { key(s) }
pub fn version_of(n: u8) -> PinSelector { version(n) }
pub fn root_of(n: u8) -> DependencyIntent { root(n) }
pub fn dependency_of(n: u8, v: u8) -> LockedDependency { dependency(n, v) }
