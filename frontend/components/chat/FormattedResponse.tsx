"use client";

import React from "react";

interface FormattedResponseProps {
  text: string;
  className?: string;
}

const FormattedResponse: React.FC<FormattedResponseProps> = ({ text, className = "" }) => {
  const renderInline = (raw: string, keyPrefix: string) => {
    const parts = raw.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return (
          <strong key={`${keyPrefix}-b${i}`} className="font-bold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
        return (
          <em key={`${keyPrefix}-e${i}`} className="italic">
            {part.slice(1, -1)}
          </em>
        );
      }
      return <React.Fragment key={`${keyPrefix}-${i}`}>{part}</React.Fragment>;
    });
  };

  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let listType: "ul" | "ol" | null = null;
  let listItems: React.ReactNode[] = [];

  const flushList = (key: string) => {
    if (listType && listItems.length > 0) {
      const listCls = "space-y-1.5 my-1.5";
      blocks.push(
        listType === "ul" ? (
          <ul key={key} className={`${listCls} list-disc pl-5 text-[0.93em] text-muted-foreground`}>
            {listItems}
          </ul>
        ) : (
          <ol key={key} className={`${listCls} list-decimal pl-5 text-[0.93em] text-muted-foreground`}>
            {listItems}
          </ol>
        )
      );
    }
    listType = null;
    listItems = [];
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    const key = `l${idx}`;

    if (!trimmed) {
      flushList(`${key}-flush`);
      blocks.push(<div key={key} className="h-2" />);
      return;
    }

    // Heading hierarchy: # = título grande/negrito, ### = subtítulo menor
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      flushList(`${key}-flush`);
      const level = headingMatch[1].length;
      const headingCls =
        level <= 1
          ? "text-[1.25em] font-bold text-foreground mt-3 mb-1.5"
          : level === 2
          ? "text-[1.12em] font-bold text-foreground mt-3 mb-1"
          : "text-[1.03em] font-semibold text-foreground mt-2.5 mb-1";
      blocks.push(
        <p key={key} className={headingCls}>
          {renderInline(headingMatch[2], key)}
        </p>
      );
      return;
    }

    // Bullet list items (tópicos menores)
    const ulMatch = trimmed.match(/^[-*•]\s+(.+)$/);
    if (ulMatch) {
      if (listType !== "ul") {
        flushList(`${key}-flush`);
        listType = "ul";
      }
      listItems.push(<li key={`${key}-li`}>{renderInline(ulMatch[1], `${key}`)}</li>);
      return;
    }

    // Numbered list items (tópicos menores)
    const olMatch = trimmed.match(/^(\d+)[.)]\s+(.+)$/);
    if (olMatch) {
      if (listType !== "ol") {
        flushList(`${key}-flush`);
        listType = "ol";
      }
      listItems.push(<li key={`${key}-li`}>{renderInline(olMatch[2], `${key}`)}</li>);
      return;
    }

    flushList(`${key}-flush`);

    // Plain paragraph
    blocks.push(
      <p key={key} className="text-[1em] leading-relaxed text-foreground">
        {renderInline(trimmed, key)}
      </p>
    );
  });

  flushList("end-flush");

  return <div className={`break-words ${className}`}>{blocks}</div>;
};

export default FormattedResponse;