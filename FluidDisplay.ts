// ═══════════════════════════════════════════════════════════════
//  FluidDisplay.ts
//  Renders the fluid scan — Mixplorer style information view
// ═══════════════════════════════════════════════════════════════

import { FluidScan, FluidFile } from "./FluidScanner";

export class FluidDisplay {

  /**
   * Render full room scan to terminal.
   * Clean, organized, information-first.
   */
  static render(scan: FluidScan): void {
    const CYAN   = "\x1b[96m";
    const GREEN  = "\x1b[92m";
    const YELLOW = "\x1b[93m";
    const DIM    = "\x1b[2m";
    const BOLD   = "\x1b[1m";
    const RESET  = "\x1b[0m";

    console.log("");
    console.log(`${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${RESET}`);
    console.log(`${CYAN}${BOLD}║  FlowStation Fluid Scan · ${scan.room.padEnd(21)}║${RESET}`);
    console.log(`${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${RESET}`);
    console.log(`${DIM}  ${scan.summary}${RESET}`);
    console.log(`${DIM}  Scanned: ${scan.scannedAt}${RESET}`);
    console.log("");

    // Group by type — Mixplorer-style organized view
    const grouped = this.groupByType(scan.files);

    for (const [type, files] of Object.entries(grouped)) {
      console.log(`${YELLOW}${BOLD}  ▸ ${type.toUpperCase()}${RESET}`);
      console.log(`${DIM}  ${"─".repeat(48)}${RESET}`);

      for (const file of files) {
        // Confidence indicator
        const conf    = Math.round(file.tag.confidence * 100);
        const confStr = conf >= 80 ? `${GREEN}●${RESET}` :
                        conf >= 50 ? `${YELLOW}●${RESET}` :
                                     `${DIM}●${RESET}`;

        console.log(
          `  ${confStr}  ${BOLD}${file.tag.name}${RESET}`
        );
        console.log(
          `${DIM}     ${file.path}${RESET}`
        );
        console.log(
          `${DIM}     Flow: ${file.flow}${RESET}`
        );

        // Show notes
        for (const note of file.tag.notes ?? []) {
          console.log(`${DIM}     💡 ${note}${RESET}`);
        }

        console.log("");
      }
    }

    // Action footer — YOUR choices
    console.log(`${CYAN}${BOLD}  ┌─ Your Actions ────────────────────────────────┐${RESET}`);
    console.log(`${CYAN}${BOLD}  │${RESET}  ${BOLD}C${RESET} Confirm tags   ${BOLD}R${RESET} Rename   ${BOLD}S${RESET} Skip          ${CYAN}${BOLD}│${RESET}`);
    console.log(`${CYAN}${BOLD}  │${RESET}  ${BOLD}L${RESET} Lock room      ${BOLD}F${RESET} Run flow  ${BOLD}Q${RESET} Quit          ${CYAN}${BOLD}│${RESET}`);
    console.log(`${CYAN}${BOLD}  └───────────────────────────────────────────────┘${RESET}`);
    console.log("");
  }

  /**
   * Show a compact one-line status per file.
   */
  static renderCompact(scan: FluidScan): void {
    const CYAN  = "\x1b[96m";
    const RESET = "\x1b[0m";
    const BOLD  = "\x1b[1m";

    console.log(`\n${CYAN}${BOLD}FlowStation · ${scan.room}${RESET}\n`);

    for (const file of scan.files) {
      const conf = Math.round(file.tag.confidence * 100);
      console.log(
        `  ${file.tag.name.padEnd(40)} ${String(conf + "%").padStart(4)}  →  ${file.flow}`
      );
    }
    console.log("");
  }

  private static groupByType(
    files: FluidFile[]
  ): Record<string, FluidFile[]> {
    const groups: Record<string, FluidFile[]> = {};
    for (const file of files) {
      const t = file.tag.type;
      if (!groups[t]) groups[t] = [];
      groups[t].push(file);
    }
    return groups;
  }
}
