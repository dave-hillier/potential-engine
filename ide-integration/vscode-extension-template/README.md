# depanalysis VS Code Extension (Template)

This directory contains a template for building a VS Code extension that integrates depanalysis architectural insights directly into the editor.

## Features (Planned)

- **Hotspot Warnings**: Visual indicators for files with high churn + complexity
- **Coupling Alerts**: Warnings when adding imports that increase coupling
- **Hover Information**: Show architectural metrics on hover
- **Code Lenses**: Inline metrics display
- **Diagnostics**: Real-time warnings for architectural issues

## Architecture

The extension uses the Language Server Protocol (LSP) to communicate with depanalysis:

```
VS Code Extension (TypeScript)
    ↓
Language Client
    ↓ (LSP Protocol)
Language Server (Python)
    ↓
depanalysis Python API
    ↓
SQLite Databases (structure.db, history.db)
```

## Implementation Guide

### 1. Set Up Extension Structure

```bash
npm install -g yo generator-code
yo code  # Select "New Language Server"
```

### 2. Install Dependencies

```json
{
  "dependencies": {
    "vscode-languageclient": "^8.0.0",
    "vscode-languageserver": "^8.0.0"
  }
}
```

### 3. Create Language Server (Python)

Use `pygls` (Python Generic Language Server):

```bash
pip install pygls
```

Example server (`server.py`):

```python
from pygls.server import LanguageServer
from pygls.lsp.methods import (
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE
)
from pygls.lsp.types import (
    Hover,
    MarkupContent,
    MarkupKind
)

from depanalysis.db_manager import DatabaseManager
from depanalysis.ide_integration import LSPServer

server = LanguageServer()
db_manager = DatabaseManager()
lsp_server = LSPServer("your-repo", db_manager)

@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls, params):
    """Provide hover information."""
    uri = params.text_document.uri
    file_path = uri.replace("file://", "")
    position = params.position

    content = lsp_server.on_hover(file_path, position.line, position.character)

    if content:
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=content
            )
        )
    return None

@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params):
    """Update diagnostics on file save."""
    uri = params.text_document.uri
    file_path = uri.replace("file://", "")

    diagnostics = lsp_server.on_diagnostic(file_path)
    ls.publish_diagnostics(uri, diagnostics)

server.start_io()
```

### 4. Configure Extension Client (TypeScript)

```typescript
import * as path from 'path';
import { workspace, ExtensionContext } from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: ExtensionContext) {
    const serverModule = context.asAbsolutePath(
        path.join('server', 'server.py')
    );

    const serverOptions: ServerOptions = {
        command: 'python',
        args: [serverModule],
        transport: TransportKind.stdio
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'python' }],
        synchronize: {
            fileEvents: workspace.createFileSystemWatcher('**/*.py')
        }
    };

    client = new LanguageClient(
        'depanalysis',
        'depanalysis Architecture Insights',
        serverOptions,
        clientOptions
    );

    client.start();
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
```

### 5. Add Visual Indicators

Use VS Code decorations API to highlight hotspots:

```typescript
import { window, TextEditorDecorationType, Range } from 'vscode';

const hotspotDecorationType = window.createTextEditorDecorationType({
    backgroundColor: 'rgba(255, 0, 0, 0.1)',
    border: '1px solid red',
    gutterIconPath: path.join(__dirname, 'icons', 'hotspot.svg'),
    overviewRulerColor: 'red',
    overviewRulerLane: 2
});

function updateDecorations(editor: TextEditor, hotspotFiles: string[]) {
    const fileName = editor.document.fileName;
    if (hotspotFiles.includes(fileName)) {
        const firstLine = new Range(0, 0, 0, 0);
        editor.setDecorations(hotspotDecorationType, [firstLine]);
    }
}
```

## Package and Publish

```bash
# Package extension
vsce package

# Publish to VS Code Marketplace
vsce publish
```

## Configuration

Add settings in `package.json`:

```json
{
  "contributes": {
    "configuration": {
      "title": "depanalysis",
      "properties": {
        "depanalysis.repoName": {
          "type": "string",
          "default": "",
          "description": "Repository name in depanalysis database"
        },
        "depanalysis.dataPath": {
          "type": "string",
          "default": "./data",
          "description": "Path to depanalysis data directory"
        },
        "depanalysis.hotspotThreshold": {
          "type": "number",
          "default": 0.7,
          "description": "Hotspot score threshold (0.0-1.0)"
        }
      }
    }
  }
}
```

## Future Enhancements

- **Code Actions**: Quick fixes for architectural issues
- **Refactoring Suggestions**: AI-powered refactoring recommendations
- **Circular Dependency Visualization**: Interactive graph view
- **Team Context**: Show who owns which modules
- **Migration Tracking**: Progress bars for migration efforts

## References

- [VS Code Extension API](https://code.visualstudio.com/api)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- [pygls Documentation](https://pygls.readthedocs.io/)
