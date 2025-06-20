import React, { useCallback } from "react";
import { Input, Button } from "antd";
import { Edit, Timer, Folder } from "lucide-react";
import {
  Component,
  TeamConfig,
  ComponentConfig,
  RoundRobinGroupChatConfig,
  SelectorGroupChatConfig,
  SolutionConfig,
} from "../../../../../types/datamodel";
import {
  isSelectorTeam,
  isRoundRobinTeam,
  isSolutionTeam,
} from "../../../../../types/guards";
import DetailGroup from "../detailgroup";

const { TextArea } = Input;

interface TeamFieldsProps {
  component: Component<TeamConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (componentType: string, id: string, parentField: string) => void;
}

export const TeamFields: React.FC<TeamFieldsProps> = ({
  component,
  onChange,
  onNavigate,
}) => {
  if (
    !isSelectorTeam(component) &&
    !isRoundRobinTeam(component) &&
    !isSolutionTeam(component)
  )
    return null;

  const handleComponentUpdate = useCallback(
    (updates: Partial<Component<ComponentConfig>>) => {
      onChange({
        ...component,
        ...updates,
        config: {
          ...component.config,
          ...(updates.config || {}),
        },
      });
    },
    [component, onChange]
  );

  const handleConfigUpdate = useCallback(
    (field: string, value: unknown) => {
      if (isSelectorTeam(component)) {
        handleComponentUpdate({
          config: {
            ...component.config,
            [field]: value,
          } as SelectorGroupChatConfig,
        });
      } else if (isRoundRobinTeam(component)) {
        handleComponentUpdate({
          config: {
            ...component.config,
            [field]: value,
          } as RoundRobinGroupChatConfig,
        });
      } else if (isSolutionTeam(component)) {
        handleComponentUpdate({
          config: {
            ...component.config,
            [field]: value,
          } as SolutionConfig,
        });
      }
    },
    [component, handleComponentUpdate]
  );

  const handleNameChange = (value: string) => {
    const updates: Partial<Component<ComponentConfig>> = { label: value };
    if (isSolutionTeam(component)) {
      updates.config = { ...component.config, name: value };
    }
    handleComponentUpdate(updates);
  };

  const handleDescriptionChange = (value: string) => {
    const updates: Partial<Component<ComponentConfig>> = { description: value };
    if (isSolutionTeam(component)) {
      updates.config = { ...component.config, description: value };
    }
    handleComponentUpdate(updates);
  };

  return (
    <div className=" ">
      <DetailGroup title="Component Details">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-primary">Name</span>
            <Input
              value={component.label || ""}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Team name"
              className="mt-1"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-primary">
              Description
            </span>
            <TextArea
              value={component.description || ""}
              onChange={(e) => handleDescriptionChange(e.target.value)}
              placeholder="Team description"
              rows={4}
              className="mt-1"
            />
          </label>
        </div>
      </DetailGroup>

      <DetailGroup title="TeamFields">
        {isSelectorTeam(component) && (
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-primary">
                Selector Prompt
              </span>
              <TextArea
                value={component.config.selector_prompt || ""}
                onChange={(e) =>
                  handleConfigUpdate("selector_prompt", e.target.value)
                }
                placeholder="Prompt for the selector"
                rows={4}
                className="mt-1"
              />
            </label>

            <div className="space-y-2">
              <h3 className="text-sm font-medium text-primary">Model</h3>
              <div className="bg-secondary p-4 rounded-md">
                {component.config.model_client ? (
                  <div className="flex items-center justify-between">
                    <span className="text-sm">
                      {component.config.model_client.config.model}
                    </span>
                    {onNavigate && (
                      <Button
                        type="text"
                        icon={<Edit className="w-4 h-4" />}
                        onClick={() =>
                          onNavigate(
                            "model",
                            component.config.model_client?.label || "",
                            "model_client"
                          )
                        }
                      />
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-secondary text-center">
                    No model configured
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {isSolutionTeam(component) && (
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-primary">
                Workspace Path
              </span>
              <Input
                value={component.config.workspace_path || ""}
                onChange={(e) =>
                  handleConfigUpdate("workspace_path", e.target.value)
                }
                placeholder="/path/to/workspace"
                className="mt-1"
                prefix={<Folder className="w-4 h-4 text-gray-400" />}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-primary">
                Backup Directory
              </span>
              <Input
                value={component.config.backup_dir || ""}
                onChange={(e) =>
                  handleConfigUpdate("backup_dir", e.target.value)
                }
                placeholder="/path/to/backup"
                className="mt-1"
                prefix={<Folder className="w-4 h-4 text-gray-400" />}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-primary">
                Requirement
              </span>
              <TextArea
                value={component.config.requirement || ""}
                onChange={(e) =>
                  handleConfigUpdate("requirement", e.target.value)
                }
                placeholder="Describe the requirement"
                rows={4}
                className="mt-1"
              />
            </label>
          </div>
        )}

        <div className="space-y-2 mt-4">
          <h3 className="text-sm font-medium text-primary">
            Termination Condition
          </h3>
          <div className="bg-secondary p-4 rounded-md">
            {component.config.termination_condition ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Timer className="w-4 h-4 text-secondary" />
                  <span className="text-sm">
                    {component.config.termination_condition.label ||
                      component.config.termination_condition.component_type}
                  </span>
                </div>
                {onNavigate && (
                  <Button
                    type="text"
                    icon={<Edit className="w-4 h-4" />}
                    onClick={() =>
                      onNavigate(
                        "termination",
                        component.config.termination_condition?.label || "",
                        "termination_condition"
                      )
                    }
                  />
                )}
              </div>
            ) : (
              <div className="text-sm text-secondary text-center">
                No termination condition configured
              </div>
            )}
          </div>
        </div>
      </DetailGroup>
    </div>
  );
};

export default React.memo(TeamFields);
