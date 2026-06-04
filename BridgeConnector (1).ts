// Add these methods to BridgeConnector.ts
// (alongside the existing methods)

  // ── Path helpers (used by MeshTreeView) ─────────────────────

  getMeshDir(): string {
    return path.join(this.root, "forge", "mesh");
  }

  getLockedDir(): string {
    return path.join(this.root, "forge", "locked");
  }

  getActiveDir(): string {
    return path.join(this.root, "forge", "active");
  }

  getAuditLogPath(): string {
    return path.join(this.root, "shared", "audit.log");
  }

  // ── Raw audit access (used by AuditTreeView) ─────────────────

  getRecentAuditRaw(limit = 200): string[] {
    const logPath = this.getAuditLogPath();
    if (!fs.existsSync(logPath)) return [];

    return fs
      .readFileSync(logPath, "utf8")
      .split("\n")
      .filter(Boolean)
      .slice(-limit);
  }
