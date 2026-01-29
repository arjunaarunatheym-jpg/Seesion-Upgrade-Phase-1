/**
 * RichTextToolbar - Simple formatting toolbar for PDF rich text
 * Inserts formatting tags at cursor position in textarea
 */
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Bold, Italic, Underline, Highlighter, AlignCenter, Minus, Type, HelpCircle } from "lucide-react";

const RichTextToolbar = ({ textareaRef, value, onChange }) => {
  
  const insertTag = (openTag, closeTag = null) => {
    const textarea = textareaRef?.current;
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.substring(start, end);
    const close = closeTag || openTag.replace('<', '</');
    
    let newText;
    if (selectedText) {
      // Wrap selected text
      newText = value.substring(0, start) + openTag + selectedText + close + value.substring(end);
    } else {
      // Insert empty tags with cursor between
      newText = value.substring(0, start) + openTag + close + value.substring(end);
    }
    
    onChange(newText);
    
    // Set cursor position after tag
    setTimeout(() => {
      textarea.focus();
      const newPos = start + openTag.length + (selectedText ? selectedText.length + close.length : 0);
      textarea.setSelectionRange(selectedText ? newPos : start + openTag.length, selectedText ? newPos : start + openTag.length);
    }, 10);
  };

  const insertLineTag = (tag) => {
    const textarea = textareaRef?.current;
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const newText = value.substring(0, start) + '\n' + tag + '\n' + value.substring(start);
    onChange(newText);
    
    setTimeout(() => {
      textarea.focus();
      const newPos = start + tag.length + 2;
      textarea.setSelectionRange(newPos, newPos);
    }, 10);
  };

  const buttons = [
    { icon: Bold, label: "Bold", action: () => insertTag('<b>', '</b>'), shortcut: "**text**" },
    { icon: Italic, label: "Italic", action: () => insertTag('<i>', '</i>'), shortcut: "*text*" },
    { icon: Underline, label: "Underline", action: () => insertTag('<u>', '</u>') },
    { icon: Highlighter, label: "Highlight", action: () => insertTag('<highlight>', '</highlight>'), className: "text-yellow-600" },
    { icon: AlignCenter, label: "Center", action: () => insertTag('<center>', '</center>') },
    { icon: Minus, label: "Line", action: () => insertLineTag('<hr>') },
  ];

  const colorButtons = [
    { color: "red", className: "bg-red-500 hover:bg-red-600" },
    { color: "blue", className: "bg-blue-500 hover:bg-blue-600" },
    { color: "green", className: "bg-green-500 hover:bg-green-600" },
  ];

  return (
    <TooltipProvider>
      <div className="flex items-center gap-1 p-2 bg-gray-100 rounded-t border border-b-0 flex-wrap">
        {/* Format buttons */}
        {buttons.map(({ icon: Icon, label, action, shortcut, className }) => (
          <Tooltip key={label}>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={action}
                className={`h-8 w-8 p-0 ${className || ''}`}
              >
                <Icon className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{label}{shortcut ? ` (${shortcut})` : ''}</p>
            </TooltipContent>
          </Tooltip>
        ))}
        
        <div className="w-px h-6 bg-gray-300 mx-1" />
        
        {/* Color buttons */}
        {colorButtons.map(({ color, className }) => (
          <Tooltip key={color}>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => insertTag(`<${color}>`, `</${color}>`)}
                className={`h-6 w-6 p-0 rounded ${className} text-white`}
              >
                <Type className="w-3 h-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{color.charAt(0).toUpperCase() + color.slice(1)} text</p>
            </TooltipContent>
          </Tooltip>
        ))}
        
        <div className="w-px h-6 bg-gray-300 mx-1" />
        
        {/* Help tooltip */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button type="button" variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400">
              <HelpCircle className="w-4 h-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <div className="text-xs space-y-1">
              <p className="font-semibold">Formatting Codes:</p>
              <p><code className="bg-gray-200 px-1">&lt;b&gt;</code> or <code className="bg-gray-200 px-1">**text**</code> = Bold</p>
              <p><code className="bg-gray-200 px-1">&lt;i&gt;</code> or <code className="bg-gray-200 px-1">*text*</code> = Italic</p>
              <p><code className="bg-gray-200 px-1">&lt;u&gt;</code> = Underline</p>
              <p><code className="bg-gray-200 px-1">&lt;highlight&gt;</code> = Yellow highlight</p>
              <p><code className="bg-gray-200 px-1">&lt;red&gt;</code> <code className="bg-gray-200 px-1">&lt;blue&gt;</code> <code className="bg-gray-200 px-1">&lt;green&gt;</code> = Colors</p>
              <p><code className="bg-gray-200 px-1">&lt;center&gt;</code> = Centered</p>
              <p><code className="bg-gray-200 px-1">&lt;hr&gt;</code> = Horizontal line</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
};

export default RichTextToolbar;
