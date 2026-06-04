import * as vscode from 'vscode';

export type MessageHandler = (message: any) => void;

export class MessageBus {
    private handlers: Map<string, MessageHandler[]> = new Map();

    public subscribe(channel: string, handler: MessageHandler): vscode.Disposable {
        if (!this.handlers.has(channel)) {
            this.handlers.set(channel, []);
        }

        this.handlers.get(channel)!.push(handler);

        return new vscode.Disposable(() => {
            const handlers = this.handlers.get(channel);
            if (handlers) {
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            }
        });
    }

    public publish(channel: string, message: any): void {
        const handlers = this.handlers.get(channel);
        if (handlers) {
            handlers.forEach(handler => handler(message));
        }
    }
}
