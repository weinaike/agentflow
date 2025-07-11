import React, { useContext, useEffect, useState } from "react";

import { Drawer, Button, message, Checkbox } from "antd";
import { Team, Session } from "../../../types/datamodel";
import ChatView from "../../playground/chat/chat";
import { appContext } from "../../../../hooks/provider";
import { sessionAPI } from "../../playground/api";
import { isSolutionTeam } from "../../../types/guards";
interface TestDrawerProps {
  isVisble: boolean;
  team: Team;
  onClose: () => void;
}

const TestDrawer = ({ isVisble, onClose, team }: TestDrawerProps) => {
  const [session, setSession] = useState<Session | null>(null);
  const { user } = useContext(appContext);
  const [loading, setLoading] = useState(false);
  const [deleteOnClose, setDeleteOnClose] = useState(true);
  const [messageApi, contextHolder] = message.useMessage();

  const createSession = async (teamId: number, teamName: string) => {
    if (!user?.id) return;
    try {
      const defaultName = `Test Session ${teamName.substring(
        0,
        20
      )} - ${new Date().toLocaleString()} `;
      const created = await sessionAPI.createSession(
        {
          name: defaultName,
          team_id: teamId,
        },
        user.id
      );
      setSession(created);
    } catch (error) {
      messageApi.error("Error creating session");
    }
  };

  const deleteSession = async (sessionId: number) => {
    if (!user?.id) return;
    try {
      await sessionAPI.deleteSession(sessionId, user.id);
      setSession(null); // Clear session state after successful deletion
    } catch (error) {
      messageApi.error("Error deleting session");
    }
  };

  // Single effect to handle session creation when drawer opens
  useEffect(() => {
    if (isVisble && team?.id && !session && !isSolutionTeam(team.component)) {
      setLoading(true);
      createSession(
        team.id,
        team.component.label || team.component.component_type
      ).finally(() => {
        setLoading(false);
      });
    }
  }, [isVisble, team?.id]);

  // Single cleanup handler in the Drawer's onClose
  const handleClose = async () => {
    if (session?.id && deleteOnClose) {
      // Only delete if flag is true
      await deleteSession(session.id);
    }
    onClose();
  };

  return (
    <div>
      {contextHolder}
      <Drawer
        title={<span>Test Team: {team.component.label}</span>}
        size="large"
        placement="right"
        onClose={handleClose}
        open={isVisble}
        extra={
          !isSolutionTeam(team.component) && (
            <Checkbox
              checked={deleteOnClose}
              onChange={(e) => setDeleteOnClose(e.target.checked)}
            >
              Delete session on close
            </Checkbox>
          )
        }
      >
        {isSolutionTeam(team.component) ? (
          <div style={{ color: 'orange', fontWeight: 500 }}>
            Solution 类型团队不支持直接对话测试。
          </div>
        ) : (
          <>
            {loading && <p>Creating a test session...</p>}
            {session && <ChatView session={session} showCompareButton={false} />}
          </>
        )}
      </Drawer>
    </div>
  );
};
export default TestDrawer;
