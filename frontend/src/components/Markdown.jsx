import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * The finalizer agent replies in Markdown, so travel plans arrive as
 * headings, bullet lists and occasional tables. Rendering that as plain
 * text would show raw `**` and `-` characters, so every message body goes
 * through here.
 *
 * react-markdown never injects raw HTML (no dangerouslySetInnerHTML), so
 * model output can't smuggle markup into the page. Each element is mapped
 * to explicit Tailwind classes rather than a typography plugin, which
 * keeps the bubble's rhythm tight and theme-aware.
 */
const components = {
  h1: (p) => <h3 className="font-display text-[17px] font-semibold tracking-tight mt-4 mb-1.5" {...p} />,
  h2: (p) => <h3 className="font-display text-[16px] font-semibold tracking-tight mt-4 mb-1.5" {...p} />,
  h3: (p) => <h4 className="font-display text-[15px] font-semibold tracking-tight mt-3.5 mb-1" {...p} />,
  h4: (p) => <h5 className="font-semibold text-[14px] mt-3 mb-1" {...p} />,
  p: (p) => <p className="my-2 leading-[1.65]" {...p} />,
  ul: (p) => <ul className="my-2 pl-4 space-y-1 list-disc marker:text-accent" {...p} />,
  ol: (p) => <ol className="my-2 pl-4 space-y-1 list-decimal marker:text-accent" {...p} />,
  li: (p) => <li className="leading-[1.6] pl-0.5" {...p} />,
  strong: (p) => <strong className="font-semibold text-ink" {...p} />,
  em: (p) => <em className="italic" {...p} />,
  hr: () => <hr className="my-3.5 border-0 border-t border-line" />,
  blockquote: (p) => (
    <blockquote className="my-2.5 border-l-2 border-accent/50 pl-3 text-muted italic" {...p} />
  ),
  a: (p) => (
    <a
      className="text-accent underline underline-offset-2 decoration-accent/40 hover:decoration-accent"
      target="_blank"
      rel="noreferrer noopener"
      {...p}
    />
  ),
  // react-markdown v10 no longer passes an `inline` flag, so inline styling
  // is applied to every <code> and reset for fenced blocks by the
  // `.md pre code` rule in index.css.
  code: (p) => (
    <code
      className="font-mono text-[0.85em] bg-surface-2 border border-line rounded px-1 py-0.5"
      {...p}
    />
  ),
  pre: (p) => (
    <pre
      className="my-2.5 bg-surface-2 border border-line rounded-lg p-3 overflow-x-auto text-[13px]"
      {...p}
    />
  ),
  table: (p) => (
    <div className="my-3 overflow-x-auto -mx-1 px-1">
      <table className="w-full text-[13px] border-collapse" {...p} />
    </div>
  ),
  th: (p) => (
    <th
      className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted border-b border-line pb-1.5 pr-4 whitespace-nowrap"
      {...p}
    />
  ),
  td: (p) => <td className="border-b border-line/60 py-1.5 pr-4 align-top" {...p} />,
};

export default function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
