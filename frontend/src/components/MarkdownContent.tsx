import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
    content: string;
    compact?: boolean;
}

/** Render model output as readable Markdown without allowing raw HTML through. */
export default function MarkdownContent({ content, compact = false }: Props) {
    return (
        <div className={`markdown-content ${compact ? "markdown-content-compact" : ""}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                skipHtml
                components={{
                    a: ({ children, ...props }) => (
                        <a {...props} target="_blank" rel="noreferrer">{children}</a>
                    ),
                    table: ({ children }) => (
                        <div className="markdown-table-wrap"><table>{children}</table></div>
                    ),
                    pre: ({ children }) => <pre className="markdown-code-block">{children}</pre>,
                    code: ({ className, children, ...props }) => (
                        <code className={className ? `markdown-code ${className}` : "markdown-code"} {...props}>
                            {children}
                        </code>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
