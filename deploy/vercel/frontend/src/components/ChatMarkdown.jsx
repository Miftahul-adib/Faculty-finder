import ReactMarkdown from "react-markdown";

export default function ChatMarkdown({ content }) {
  return (
    <div className="chat-markdown">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
