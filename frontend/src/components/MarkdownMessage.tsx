import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

type MarkdownMessageProps = {
  content: string;
};

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const text = content?.trim() ?? "";

  if (!text) {
    return null;
  }

  return (
    <div className="chat-message-body chat-markdown">
      <ReactMarkdown rehypePlugins={[rehypeKatex]} remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]} skipHtml>
        {text}
      </ReactMarkdown>
    </div>
  );
}
