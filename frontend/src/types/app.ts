export type AsyncStatus = "pending" | "running" | "done" | "failed";

export type ActivityItem = {
  id: string;
  title: string;
  description: string;
  time: string;
};
