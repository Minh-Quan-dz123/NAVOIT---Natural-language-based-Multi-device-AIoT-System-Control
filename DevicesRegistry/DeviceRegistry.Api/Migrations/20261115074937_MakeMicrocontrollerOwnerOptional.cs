using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DeviceRegistry.Api.Migrations
{
    /// <inheritdoc />
    public partial class MakeMicrocontrollerOwnerOptional : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Microcontrollers_Users_UserId",
                table: "Microcontrollers");

            migrationBuilder.AlterColumn<int>(
                name: "UserId",
                table: "Microcontrollers",
                type: "integer",
                nullable: true,
                oldClrType: typeof(int),
                oldType: "integer");

            migrationBuilder.AddForeignKey(
                name: "FK_Microcontrollers_Users_UserId",
                table: "Microcontrollers",
                column: "UserId",
                principalTable: "Users",
                principalColumn: "Id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Microcontrollers_Users_UserId",
                table: "Microcontrollers");

            migrationBuilder.AlterColumn<int>(
                name: "UserId",
                table: "Microcontrollers",
                type: "integer",
                nullable: false,
                defaultValue: 0,
                oldClrType: typeof(int),
                oldType: "integer",
                oldNullable: true);

            migrationBuilder.AddForeignKey(
                name: "FK_Microcontrollers_Users_UserId",
                table: "Microcontrollers",
                column: "UserId",
                principalTable: "Users",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
