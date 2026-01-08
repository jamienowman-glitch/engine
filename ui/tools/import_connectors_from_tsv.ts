import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';
import axios from 'axios';

// Interfaces
interface TSVRow {
    platform_id: string;
    scope_id: string;
    scope_name: string;
    scope_type: string;
    scope_description: string;
    required_for_mvp: string;
    mvp_reason: string;
    danger_level: string;
    notes: string;
    source_urls: string;
}

interface ToolDefinition {
    id: string;
    name: string;
    description: string;
    auth_config: {
        type: string;
        secret_ref: string;
    };
    scopes: Record<string, ToolScope>;
}

interface ToolScope {
    id: string;
    name: string;
    description: string;
    firearms_required: boolean;
    rationale: string;
}

const API_BASE = "http://localhost:8000"; // Verify port?

async function main() {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.error("Usage: tsx import_connectors_from_tsv.ts <file1.tsv> <file2.tsv> ...");
        process.exit(1);
    }

    const reportPath = path.resolve("docs/workbench/tsv_import/CONNECTOR_IMPORT_REPORT.md");
    const reportLines: string[] = [];
    reportLines.push("# Connector Import Report");
    reportLines.push(`Date: ${new Date().toISOString()}`);
    reportLines.push("");

    const platforms = new Map<string, TSVRow[]>();

    // 1. Parse Inputs
    for (const filePath of args) {
        console.log(`Reading ${filePath}...`);
        const content = fs.readFileSync(filePath, 'utf-8');
        const rows = parse(content, {
            columns: true,
            delimiter: '\t',
            skip_empty_lines: true
        }) as TSVRow[];

        for (const row of rows) {
            if (!row.platform_id) continue;
            const pid = row.platform_id.toLowerCase().trim();
            if (!platforms.has(pid)) {
                platforms.set(pid, []);
            }
            platforms.get(pid)?.push(row);
        }
    }

    reportLines.push(`Total Platforms Found: ${platforms.size}`);
    let totalScopes = 0;
    platforms.forEach(rows => totalScopes += rows.length);
    reportLines.push(`Total Scopes Found: ${totalScopes}`);
    reportLines.push("");

    // 2. Process Platforms
    reportLines.push("## Import Status");
    reportLines.push("| Platform | Status | Secret Ref | Scopes Count |");
    reportLines.push("|---|---|---|---|");

    for (const [pid, rows] of platforms.entries()) {
        const toolId = pid;
        const toolName = pid.charAt(0).toUpperCase() + pid.slice(1);

        // Determine Secret Ref
        // Look in notes for "secret_ref: xyz"
        let secretRef = "REQUIRED_SECRET_NAME_TBD";
        for (const r of rows) {
            if (r.notes && r.notes.includes("secret_ref:")) {
                const match = r.notes.match(/secret_ref:\s*([^\s,]+)/);
                if (match) {
                    secretRef = match[1];
                    break;
                }
            }
        }

        // Build Definition
        const toolDef: ToolDefinition = {
            id: toolId,
            name: toolName,
            description: `MCP Connector for ${toolName}. Imported from TSV.`,
            auth_config: {
                type: "oauth2", // Default assumption, or check notes?
                secret_ref: secretRef
            },
            scopes: {}
        };

        for (const r of rows) {
            toolDef.scopes[r.scope_id] = {
                id: r.scope_id,
                name: r.scope_name,
                description: r.scope_description,
                firearms_required: false, // NON-NEGOTIABLE
                rationale: `Imported. Danger: ${r.danger_level}. MVP: ${r.required_for_mvp}`
            };
        }

        // 3. Upsert Draft
        let status = "Unknown";
        try {
            const url = `${API_BASE}/workbench/drafts/${toolId}`;
            // MOCKING the call if API is not running, or formatting properly.
            // Assumption: User wants REAL call. If fails, I catch.
            // But wait, "ui repo only... do not touch engines".
            // I can't start the engines.
            // If engines aren't running, this will fail.
            // I will implement a "files only" mode fallback or just try catch?
            // "Goal: The goal is: the drafts appear when I open the Workbench... persistence path that the current Workbench uses"
            // If I can't hit the API, I can't persist.
            // I'll try to hit it.

            // NOTE: Since I am an agent, I might not have the server running.
            // But the instructions "call the Workbench Draft endpoints" implies I should try.

            await axios.put(url, toolDef);
            status = "✅ Success";
        } catch (e: any) {
            status = `❌ Failed (${e.message})`;
            // If connection refused, write to a standalone file?
            // "Use the actual Workbench Draft persistence path"
            // If I can't hit API, I can't do this.
            // I will log the JSON to a debug dir.
            const debugDir = path.resolve("docs/workbench/tsv_import/debug_payloads");
            if (!fs.existsSync(debugDir)) fs.mkdirSync(debugDir, { recursive: true });
            fs.writeFileSync(path.join(debugDir, `${toolId}.json`), JSON.stringify(toolDef, null, 2));
            status += " (Saved to debug)";
        }

        reportLines.push(`| ${toolId} | ${status} | \`${secretRef}\` | ${rows.length} |`);
    }

    fs.writeFileSync(reportPath, reportLines.join("\n"));
    console.log(`Report written to ${reportPath}`);
}

main().catch(console.error);
