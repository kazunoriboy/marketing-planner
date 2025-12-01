# Prompt: Create a "Ryokan AI Marketing Support Tool" Frontend using Next.js

## 1. Overall Objective

Create a frontend application for a "Ryokan AI Marketing Support Tool" using **Next.js with the App Router**. The application should be a single-page interface where different views are rendered dynamically on the client side. All UI components should be defined within a single main page file for simplicity.

## 2. Project Setup & Tech Stack

1. **Initialize Project:** Start with a standard Next.js project setup using `npx create-next-app@latest`. Ensure the following options are selected:
    
    - **Use TypeScript?** Yes
        
    - **Use ESLint?** Yes
        
    - **Use Tailwind CSS?** Yes
        
    - **Use `src/` directory?** No
        
    - **Use App Router?** Yes
        
2. **Install Dependencies:** After setup, install the `lucide-react` library for icons: `npm install lucide-react`.
    
3. **Language:** All user-facing text (titles, buttons, descriptions) must be in **Japanese**.
    

## 3. Global Styles & Layout

### 3.1. `app/globals.css`

Define the following global styles:

- **Base Layers:** Set up standard `@tailwind base`, `@tailwind components`, `@tailwind utilities`.
    
- **Body Styling:** In the `base` layer, style the `body` with a `bg-slate-950` background and `text-slate-200` color.
    
- **Component Layer:** Create a `.glass-card` component with the style: `@apply bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl;`
    
- **Utility Layer:** Create a `.animate-fadeIn` utility with a corresponding `@keyframes fadeIn` rule for a subtle fade-in and upward transition effect.
    

### 3.2. `app/layout.jsx`

- This should be a standard root layout file.
    
- Import and use the **"Inter"** font from `next/font/google`.
    
- Set the HTML language to Japanese (`lang="ja"`).
    
- Set the page title and description in the `metadata` object.
    
- Apply the Inter font class to the `<body>` tag.
    

### 3.3. `tailwind.config.js`

- Ensure the `content` array is correctly configured to scan files within the `./app/**/*.{js,ts,jsx,tsx,mdx}` directory.
    

## 4. Main Application Component (`app/page.jsx`)

This will be the primary file containing all UI logic.

- **Client Component:** The file must start with the `'use client';` directive.
    
- **State Management:** Use the `useState` hook to manage the currently active view (e.g., `const [activeView, setActiveView] = useState('dashboard');`).
    
- **Imports:** Import `useState` from 'react' and all necessary icons from `lucide-react`.
    

### 4.1. Component Breakdown (Define these inside `app/page.jsx`)

#### 4.1.1. `Sidebar` Component

- A functional component that receives `activeView` and `setActiveView` as props.
    
- **Layout:** A fixed-width (`w-64`) flex column with the `.glass-card` style.
    
- **Header:** Contains a `BrainCircuit` icon with a purple-to-cyan gradient background and the application title 「旅館AIアシスタント」.
    
- **Navigation:**
    
    - Map over an array of navigation items (`navItems`).
        
    - Each item should have an `id`, `icon`, and `label` in Japanese.
        
    - Render an `<a>` tag for each item with an `onClick` handler that calls `setActiveView(item.id)`.
        
    - Apply a conditional background color (`bg-white/10`) if `activeView === item.id`.
        
- **Footer:** A "設定" link with a `Settings` icon at the bottom.
    

#### 4.1.2. Content View Components

Create a separate functional component for each view. Each should have the `animate-fadeIn` class on its root `<section>` element.

- **`Dashboard` Component:**
    
    - A main title 「ダッシュボード」 and a welcome message.
        
    - A large `.glass-card` for "AIからの提案" featuring a `Sparkles` icon.
        
    - A 3-column grid of smaller `.glass-card`s for "ターゲット顧客", "旅館の強み・弱み", and "競合の動向". Use appropriate icons (`UserCheck`, `Swords`, `Building`).
        
- **`Persona` Component:**
    
    - A main title 「顧客を知る」 and a descriptive paragraph.
        
    - A primary CTA button ("新しいペルソナを作成") with a gradient background and a `Plus` icon.
        
    - A grid displaying example persona cards, each being a `.glass-card` with a placeholder image, name, and description.
        
- **`Market` Component:**
    
    - A main title 「市場を知る」 and a descriptive paragraph.
        
    - A `.glass-card` for "口コミ分析サマリー" with a 2-column grid comparing "あなたの旅館" and "競合A".
        
- **`Planner` Component:**
    
    - A main title 「プランを立てる」 and a descriptive paragraph.
        
    - A `.glass-card` for "アイデア生成ワークスペース" containing a text input and a "アイデアを生成" button with a gradient.
        
- **`Content` Component:**
    
    - A main title 「発信する」 and a descriptive paragraph.
        
    - A `.glass-card` for "SNS投稿ジェネレーター" with `<select>` dropdowns, a full-width CTA button ("Instagramの投稿を作成"), and a styled preview area for the generated text.
        

### 4.2. `Home` Page Component (Default Export)

- This is the main component that orchestrates the UI.
    
- It will hold the `activeView` state.
    
- **Render Logic:** Create a `renderContent` function that uses a `switch` statement on `activeView` to return the appropriate content component (`Dashboard`, `Persona`, etc.).
    
- **Final JSX:**
    
    - The root element should be a `<main>` tag with `className="flex h-screen overflow-hidden"`.
        
    - It should render the `<Sidebar>` component, passing the state and setter function.
        
    - Next to the sidebar, render the dynamic content area by calling the `renderContent()` function inside a `div` with `className="flex-1 p-8 overflow-y-auto"`.
        

Please generate the code for the four files (`layout.jsx`, `globals.css`, `tailwind.config.js`, and `page.jsx`) based on these detailed instructions.