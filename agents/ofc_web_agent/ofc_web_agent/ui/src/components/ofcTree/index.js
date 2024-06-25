import React, { useState, useEffect } from 'react';

export const parseToTree = (paths) => {
  const root = {};
  console.log("paths: " + JSON.stringify(paths));
  paths.forEach(path => {
    // Check for leading "/" and remove it
    console.log("Checking path: " + path);
    const cleanedPath = path.startsWith('/') ? path.slice(1) : path;
    console.log("cleanedPath: " + cleanedPath);
    const fields = cleanedPath.split('/');
    let current = root;

    fields.forEach((field, index) => {
      if (!current[field]) {
        current[field] = {};
      }
      if (index === fields.length - 1) {
        current[field]._fullPath = cleanedPath; // Use cleanedPath
      }
      current = current[field];
    });
  });

  console.log("paths: " + JSON.stringify(paths));
  console.log("root: " + JSON.stringify(root));
  return root;
};

export const TreeNode = ({
  node,
  name,
  onNodeClick,
  path = '',
  section,
  selectedItem
}) => {
  const [internallyControlledExpansion, setInternallyControlledExpansion] = useState(false);
  const hasChildren = Object.keys(node).some(key => key !== '_fullPath');
  const isSelected = selectedItem === (path + name).replace('//', '/');

  const handleExpandClick = (e) => {
    e.stopPropagation(); // Stops the click from bubbling up to other click handlers
    setInternallyControlledExpansion(!internallyControlledExpansion);
  };

  const handleTextClick = (e) => {
    e.stopPropagation(); // Again, prevent the click from affecting other elements
    onNodeClick(path + name, section);
  };

  return (
    <div>
      <div
        style={{
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          backgroundColor: isSelected ? '#333' : 'transparent',
          color: isSelected ? '#1E88E5' : '#FFFFFF',
          padding: '2px 5px',
          borderRadius: '4px',
        }}
      >
        {hasChildren ? (
          <span onClick={handleExpandClick} style={{ marginRight: '5px', fontWeight: 'bold' }}>
            {internallyControlledExpansion ? '[-]' : '[+]'}
          </span>
        ) : (
          <span style={{ width: '16px' }}></span> // Empty space to align items without children
        )}
        <span onClick={handleTextClick} style={{ flex: 1 }}>
          {name}
        </span>
      </div>
      {internallyControlledExpansion && hasChildren && (
        <div style={{ marginLeft: '20px' }}>
          {Object.entries(node).map(([key, value]) => {
            if (key !== '_fullPath') {
              // Construct the full path for the next level in the tree
              const childPath = path + name + '/';
              return (
                <TreeNode
                  key={key}
                  name={key}
                  node={value}
                  onNodeClick={onNodeClick}
                  path={childPath}
                  section={section}
                  selectedItem={selectedItem} // Passing selectedItem down for recursive selection checking
                />
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
};

export default TreeNode;
