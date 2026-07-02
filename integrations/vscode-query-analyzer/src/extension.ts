import * as vscode from "vscode";

import {
  ConnectionPayload,
  buildAnalyzePayload,
  postAnalyze,
  postAiAnalyze,
  renderAnalysisHtml
} from "./apiClient";
import {
  ProfilesConfig,
  SUPPORTED_ENGINES,
  QueryAnalyzerProfile,
  buildProfileDescription,
  defaultProfileAfterDelete,
  defaultProfileAfterRename,
  defaultPortForEngine,
  deleteProfile,
  profilesFromConfig,
  renameProfile,
  upsertProfile
} from "./profiles";
import { resolveApiUrl, ServerManager } from "./serverManager";

const PASSWORD_PREFIX = "queryAnalyzer.profilePassword.";
const EDIT_PROFILE_BUTTON: vscode.QuickInputButton = {
  iconPath: new vscode.ThemeIcon("edit"),
  tooltip: "Edit profile"
};
const DELETE_PROFILE_BUTTON: vscode.QuickInputButton = {
  iconPath: new vscode.ThemeIcon("trash"),
  tooltip: "Delete profile"
};

let serverManager: ServerManager | undefined;

type ProfileQuickPickItem = vscode.QuickPickItem & {
  itemType: "profile" | "create";
  profile?: QueryAnalyzerProfile;
};

type ProfileQuickPickResult =
  | { kind: "select"; profile: QueryAnalyzerProfile }
  | { kind: "create" }
  | { kind: "edit"; profile: QueryAnalyzerProfile }
  | { kind: "delete"; profile: QueryAnalyzerProfile }
  | { kind: "cancel" };

interface ProfileFormResult {
  profile: QueryAnalyzerProfile;
  password?: string;
  passwordChanged: boolean;
}

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel("Query Analyzer");
  serverManager = new ServerManager(context.extensionPath, output);

  const disposable = vscode.commands.registerCommand("query-analyzer.analyze", async () => {
    const editor = vscode.window.activeTextEditor;
    const selectedText = editor?.document.getText(editor.selection).trim();

    if (!selectedText) {
      vscode.window.showWarningMessage("Select a SQL query before running Query Analyzer.");
      return;
    }

    const config = vscode.workspace.getConfiguration("queryAnalyzer");
    const profile = await selectProfile(context);

    if (!profile) {
      return;
    }
    const profileWithPassword = await ensureProfilePassword(profile, context);

    if (!profileWithPassword) {
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "queryAnalyzerResults",
      "Query Analyzer",
      vscode.ViewColumn.Beside,
      { enableScripts: false }
    );

    panel.webview.html = renderAnalysisHtml({
      success: true,
      plan_summary: "Analyzing selected query..."
    });

    try {
      const apiUrl = await resolveApiUrl(config, serverManager!);
      const result = await postAnalyze(
        apiUrl,
        buildAnalyzePayload(selectedText, profileWithPassword.connection)
      );
      panel.webview.html = renderAnalysisHtml(result);

      if (result.success && (result.raw_plan || result.plan_summary) && result.engine) {
        void renderAiAnalysisWhenReady(panel, apiUrl, result);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      panel.webview.html = renderAnalysisHtml({
        success: false,
        error: `Could not start or reach Query Analyzer API: ${message}`
      });
      output.show(true);
    }
  });

  context.subscriptions.push(disposable, output, { dispose: () => serverManager?.dispose() });
}

export function deactivate(): void {
  serverManager?.dispose();
}

async function renderAiAnalysisWhenReady(
  panel: vscode.WebviewPanel,
  apiUrl: string,
  result: Awaited<ReturnType<typeof postAnalyze>>
): Promise<void> {
  try {
    const aiResult = await postAiAnalyze(apiUrl, {
      plan_json: result.raw_plan ?? result.plan_summary ?? "No plan available",
      query: result.query ?? "",
      engine: result.engine ?? ""
    });

    panel.webview.html = renderAnalysisHtml({
      ...result,
      ai_analysis: aiResult.success
        ? {
            summary: aiResult.summary,
            observations: aiResult.observations ?? [],
            recommendations: aiResult.recommendations ?? [],
            suggested_query: aiResult.suggested_query ?? null,
            raw_response: aiResult.raw_response ?? null
          }
        : null
    });
  } catch {
    panel.webview.html = renderAnalysisHtml({
      ...result,
      ai_analysis: null
    });
  }
}

async function selectProfile(
  context: vscode.ExtensionContext
): Promise<QueryAnalyzerProfile | undefined> {
  while (true) {
    const config = queryAnalyzerConfig();
    const configuredProfiles = config.get<ProfilesConfig>("profiles", {});
    const profiles = await withStoredPasswords(profilesFromConfig(configuredProfiles), context);

    if (profiles.length === 0) {
      const create = "Create Query Analyzer profile";
      const selected = await vscode.window.showInformationMessage(
        "No Query Analyzer profiles configured.",
        create
      );
      return selected === create ? createProfile(config, context, configuredProfiles) : undefined;
    }

    const action = await pickProfileAction(
      profiles,
      config.get<string>("defaultProfile", "")
    );

    if (action.kind === "cancel") {
      return undefined;
    }
    if (action.kind === "select") {
      return action.profile;
    }
    if (action.kind === "create") {
      return createProfile(config, context, configuredProfiles);
    }
    if (action.kind === "edit") {
      await editProfile(config, context, action.profile);
    }
    if (action.kind === "delete") {
      await removeProfile(config, context, action.profile);
    }
  }
}

async function withStoredPasswords(
  profiles: QueryAnalyzerProfile[],
  context: vscode.ExtensionContext
): Promise<QueryAnalyzerProfile[]> {
  const resolved: QueryAnalyzerProfile[] = [];

  for (const profile of profiles) {
    const password = await context.secrets.get(`${PASSWORD_PREFIX}${profile.name}`);
    resolved.push({
      ...profile,
      connection: password ? { ...profile.connection, password } : profile.connection
    });
  }

  return resolved;
}

function pickProfileAction(
  profiles: QueryAnalyzerProfile[],
  defaultProfile: string
): Promise<ProfileQuickPickResult> {
  return new Promise((resolve) => {
    const quickPick = vscode.window.createQuickPick<ProfileQuickPickItem>();
    let settled = false;

    const settle = (result: ProfileQuickPickResult): void => {
      if (settled) {
        return;
      }
      settled = true;
      quickPick.hide();
      quickPick.dispose();
      resolve(result);
    };

    quickPick.placeholder = "Choose the Query Analyzer profile for this analysis";
    quickPick.matchOnDescription = true;
    quickPick.items = buildProfileQuickPickItems(profiles, defaultProfile);

    quickPick.onDidAccept(() => {
      const selected = quickPick.selectedItems[0];
      if (!selected) {
        return;
      }
      if (selected.itemType === "create") {
        settle({ kind: "create" });
        return;
      }
      if (selected.profile) {
        settle({ kind: "select", profile: selected.profile });
      }
    });

    quickPick.onDidTriggerItemButton((event) => {
      if (!event.item.profile) {
        return;
      }
      if (event.button === EDIT_PROFILE_BUTTON) {
        settle({ kind: "edit", profile: event.item.profile });
      }
      if (event.button === DELETE_PROFILE_BUTTON) {
        settle({ kind: "delete", profile: event.item.profile });
      }
    });

    quickPick.onDidHide(() => settle({ kind: "cancel" }));
    quickPick.show();
  });
}

function buildProfileQuickPickItems(
  profiles: QueryAnalyzerProfile[],
  defaultProfile: string
): ProfileQuickPickItem[] {
  return [
    ...profiles.map((profile) => ({
      itemType: "profile" as const,
      label: profile.name === defaultProfile ? `$(star-full) ${profile.name}` : profile.name,
      description: buildProfileDescription(profile),
      buttons: [EDIT_PROFILE_BUTTON, DELETE_PROFILE_BUTTON],
      profile
    })),
    {
      itemType: "create" as const,
      label: "$(add) Create new profile",
      description: "Add a database connection profile"
    }
  ];
}

async function ensureProfilePassword(
  profile: QueryAnalyzerProfile,
  context: vscode.ExtensionContext
): Promise<QueryAnalyzerProfile | undefined> {
  if (!profileNeedsPassword(profile)) {
    return profile;
  }

  const selected = await vscode.window.showWarningMessage(
    `Profile '${profile.name}' has no stored password.`,
    "Enter Password",
    "Continue Without Password"
  );

  if (selected === "Continue Without Password") {
    return profile;
  }
  if (selected !== "Enter Password") {
    return undefined;
  }

  const password = await vscode.window.showInputBox({
    title: "Query Analyzer Profile",
    prompt: `Password for profile '${profile.name}' (stored in VS Code SecretStorage)`,
    password: true
  });

  if (password === undefined) {
    return undefined;
  }
  if (!password) {
    return profile;
  }

  await context.secrets.store(passwordKey(profile.name), password);

  return {
    ...profile,
    connection: {
      ...profile.connection,
      password
    }
  };
}

function profileNeedsPassword(profile: QueryAnalyzerProfile): boolean {
  const engine = stringValue(profile.connection.engine);
  return (
    engine !== "sqlite" &&
    Boolean(stringValue(profile.connection.username)) &&
    !stringValue(profile.connection.password)
  );
}

async function createProfile(
  config: vscode.WorkspaceConfiguration,
  context: vscode.ExtensionContext,
  configuredProfiles: ProfilesConfig
): Promise<QueryAnalyzerProfile | undefined> {
  const form = await promptProfile(configuredProfiles);
  if (!form) {
    return undefined;
  }

  if (form.passwordChanged && form.password) {
    await context.secrets.store(passwordKey(form.profile.name), form.password);
  }

  const target = configurationTarget();
  await config.update("profiles", upsertProfile(configuredProfiles, profileForConfig(form.profile)), target);
  await config.update("defaultProfile", form.profile.name, target);

  vscode.window.showInformationMessage(`Query Analyzer profile '${form.profile.name}' created.`);
  return form.profile;
}

async function editProfile(
  config: vscode.WorkspaceConfiguration,
  context: vscode.ExtensionContext,
  existingProfile: QueryAnalyzerProfile
): Promise<QueryAnalyzerProfile | undefined> {
  const configuredProfiles = config.get<ProfilesConfig>("profiles", {});
  const form = await promptProfile(configuredProfiles, existingProfile);
  if (!form) {
    return undefined;
  }

  const existingPassword =
    (await context.secrets.get(passwordKey(existingProfile.name))) ??
    stringValue(existingProfile.connection.password);
  const usesPassword = stringValue(form.profile.connection.engine) !== "sqlite";
  const passwordToStore = usesPassword
    ? form.passwordChanged
      ? form.password
      : existingPassword || undefined
    : undefined;
  const profileForUse = passwordToStore
    ? {
        ...form.profile,
        connection: { ...form.profile.connection, password: passwordToStore }
      }
    : form.profile;
  const target = configurationTarget();

  await config.update(
    "profiles",
    renameProfile(configuredProfiles, existingProfile.name, profileForConfig(profileForUse)),
    target
  );
  await config.update(
    "defaultProfile",
    defaultProfileAfterRename(
      config.get<string>("defaultProfile", ""),
      existingProfile.name,
      profileForUse.name
    ),
    target
  );

  if (passwordToStore) {
    await context.secrets.store(passwordKey(profileForUse.name), passwordToStore);
  } else {
    await context.secrets.delete(passwordKey(profileForUse.name));
  }
  if (existingProfile.name !== profileForUse.name) {
    await context.secrets.delete(passwordKey(existingProfile.name));
  }

  vscode.window.showInformationMessage(`Query Analyzer profile '${profileForUse.name}' updated.`);
  return profileForUse;
}

async function removeProfile(
  config: vscode.WorkspaceConfiguration,
  context: vscode.ExtensionContext,
  profile: QueryAnalyzerProfile
): Promise<boolean> {
  const selected = await vscode.window.showWarningMessage(
    `Delete Query Analyzer profile '${profile.name}'?`,
    { modal: true },
    "Delete"
  );

  if (selected !== "Delete") {
    return false;
  }

  const configuredProfiles = config.get<ProfilesConfig>("profiles", {});
  const target = configurationTarget();

  await config.update("profiles", deleteProfile(configuredProfiles, profile.name), target);
  await config.update(
    "defaultProfile",
    defaultProfileAfterDelete(config.get<string>("defaultProfile", ""), profile.name),
    target
  );
  await context.secrets.delete(passwordKey(profile.name));

  vscode.window.showInformationMessage(`Query Analyzer profile '${profile.name}' deleted.`);
  return true;
}

async function promptProfile(
  configuredProfiles: ProfilesConfig,
  existingProfile?: QueryAnalyzerProfile
): Promise<ProfileFormResult | undefined> {
  const existingConnection = existingProfile?.connection ?? {};
  const name = await vscode.window.showInputBox({
    title: "Query Analyzer Profile",
    prompt: "Profile name",
    value: existingProfile?.name ?? "",
    validateInput: (value) => {
      const trimmed = value.trim();
      if (!trimmed) {
        return "Profile name is required.";
      }
      if (trimmed !== existingProfile?.name && configuredProfiles[trimmed]) {
        return "A profile with this name already exists.";
      }
      return undefined;
    }
  });

  if (!name) {
    return undefined;
  }

  const currentEngine = stringValue(existingConnection.engine);
  const engines = currentEngine
    ? [currentEngine, ...SUPPORTED_ENGINES.filter((engine) => engine !== currentEngine)]
    : [...SUPPORTED_ENGINES];
  const engine = await vscode.window.showQuickPick(engines, {
    title: "Query Analyzer Profile",
    placeHolder: "Database engine"
  });

  if (!engine) {
    return undefined;
  }

  const database = await vscode.window.showInputBox({
    title: "Query Analyzer Profile",
    prompt: engine === "sqlite" ? "SQLite database path or :memory:" : "Database name",
    value: stringValue(existingConnection.database) || (engine === "sqlite" ? ":memory:" : "")
  });

  if (database === undefined) {
    return undefined;
  }

  const connection: ConnectionPayload = {
    engine,
    database
  };

  if (engine !== "sqlite") {
    const host = await vscode.window.showInputBox({
      title: "Query Analyzer Profile",
      prompt: "Host",
      value: stringValue(existingConnection.host) || "localhost"
    });

    if (host === undefined) {
      return undefined;
    }

    const defaultPort = defaultPortForEngine(engine);
    const port = await vscode.window.showInputBox({
      title: "Query Analyzer Profile",
      prompt: "Port",
      value: portValue(existingConnection.port) || (defaultPort ? String(defaultPort) : ""),
      validateInput: (value) => {
        if (!value.trim()) {
          return undefined;
        }
        const parsed = Number(value);
        return Number.isInteger(parsed) && parsed > 0 && parsed <= 65535
          ? undefined
          : "Port must be a number between 1 and 65535.";
      }
    });

    if (port === undefined) {
      return undefined;
    }

    const username = await vscode.window.showInputBox({
      title: "Query Analyzer Profile",
      prompt: "Username (optional)",
      value: stringValue(existingConnection.username)
    });

    if (username === undefined) {
      return undefined;
    }

    const password = await vscode.window.showInputBox({
      title: "Query Analyzer Profile",
      prompt: existingProfile
        ? "Password (optional, leave blank to keep current)"
        : "Password (optional, stored in VS Code SecretStorage)",
      password: true
    });

    if (password === undefined) {
      return undefined;
    }

    connection.host = host;
    if (port.trim()) {
      connection.port = Number(port);
    }
    if (username.trim()) {
      connection.username = username;
    }
    if (password) {
      connection.password = password;
    }

    return {
      profile: {
        name: name.trim(),
        connection
      },
      password,
      passwordChanged: password.length > 0
    };
  }

  return {
    profile: {
      name: name.trim(),
      connection
    },
    passwordChanged: false
  };
}

function profileForConfig(profile: QueryAnalyzerProfile): QueryAnalyzerProfile {
  return {
    ...profile,
    connection: connectionForConfig(profile.connection)
  };
}

function connectionForConfig(connection: ConnectionPayload): ConnectionPayload {
  const nextConnection = { ...connection };
  delete nextConnection.password;
  return nextConnection;
}

function configurationTarget(): vscode.ConfigurationTarget {
  return vscode.workspace.workspaceFolders
    ? vscode.ConfigurationTarget.Workspace
    : vscode.ConfigurationTarget.Global;
}

function queryAnalyzerConfig(): vscode.WorkspaceConfiguration {
  return vscode.workspace.getConfiguration("queryAnalyzer");
}

function passwordKey(profileName: string): string {
  return `${PASSWORD_PREFIX}${profileName}`;
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function portValue(value: unknown): string {
  return typeof value === "number" && Number.isInteger(value) ? String(value) : stringValue(value);
}
