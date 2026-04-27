import type React from "react";
import { BadgeCheck, BookOpen, Boxes, Brain, Code2, Filter, Landmark, Newspaper, Sparkles } from "lucide-react";
import type { CategoryStat } from "../types";

const categoryIcons: Record<string, React.ReactNode> = {
  全部: <Newspaper size={16} />,
  大模型: <Brain size={16} />,
  产品更新: <Sparkles size={16} />,
  Agent: <BadgeCheck size={16} />,
  多模态: <Boxes size={16} />,
  开发者: <Code2 size={16} />,
  研究论文: <BookOpen size={16} />,
  商业政策: <Landmark size={16} />,
};

type CategoryFilterProps = {
  categories: CategoryStat[];
  activeCategory: string;
  onCategoryChange: (category: string) => void;
};

export function CategoryFilter({ categories, activeCategory, onCategoryChange }: CategoryFilterProps) {
  return (
    <nav className="categoryFilter" aria-label="分类筛选">
      {categories.map(([category, count]) => (
        <button
          key={category}
          className={category === activeCategory ? "categoryButton isActive" : "categoryButton"}
          onClick={() => onCategoryChange(category)}
        >
          <span className="categoryName">
            {categoryIcons[category] || <Filter size={16} />}
            {category}
          </span>
          <span className="categoryCount">{count}</span>
        </button>
      ))}
    </nav>
  );
}
